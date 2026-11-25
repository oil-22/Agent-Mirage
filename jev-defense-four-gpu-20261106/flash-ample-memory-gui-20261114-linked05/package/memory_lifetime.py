"""Process-local early release of dead temporaries; preserve every numerical AST node."""
import ast,copy,hashlib,inspect,json,sys,time,types
from pathlib import Path

class RemoveDeletes(ast.NodeTransformer):
    def visit_Delete(self,node):return None
    def visit_If(self,node):
        node=self.generic_visit(node)
        return node if node.body else None

def arithmetic_ast(source):
    tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef));fn.decorator_list=[]
    tree=ast.Module(body=[fn],type_ignores=[]);tree=RemoveDeletes().visit(tree);ast.fix_missing_locations(tree)
    return ast.dump(tree,include_attributes=False)

def tensor(torch,value,path,source=None):
    from evidence_store import store
    x=value.detach().cpu().contiguous();raw=x.view(torch.uint8).numpy().tobytes();mode=store(path,raw,source)
    return {'shape':list(x.shape),'dtype':str(x.dtype),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'file':path.name,'storage':mode}

def run_kernel_tests(torch,baseline,optimized,config):
    cases=[]
    specs=[('cpu',1,2,8,False,False,64),('cpu',65,2,16,True,True,64),('cpu',3,2,8,False,True,1)]
    heads=config.linear_num_value_heads;dim=config.linear_key_head_dim;vdim=config.linear_value_head_dim
    specs += [('cuda:0',n,heads,dim,norm,state,chunk)for n,norm,state,chunk in [(1,True,True,64),(63,True,False,64),(64,False,True,64),(65,True,True,64),(129,False,False,64),(257,True,True,64)]]
    with torch.inference_mode():
        for device,n,h,d,norm,state,chunk in specs:
            torch.manual_seed(137+n)
            q=torch.randn(1,n,h,d,device=device,dtype=torch.bfloat16)*0.05
            k=torch.randn_like(q)*0.05;v=torch.randn(1,n,h,vdim if device.startswith('cuda')else d,device=device,dtype=torch.bfloat16)*0.05
            g=-torch.rand(1,n,h,device=device,dtype=torch.float32)*0.1;beta=torch.rand(1,n,h,device=device,dtype=torch.bfloat16)
            initial=torch.randn(1,h,d,v.shape[-1],device=device,dtype=torch.float32)*0.01 if state else None
            kwargs={'g':g,'beta':beta,'chunk_size':chunk,'initial_state':initial,'output_final_state':state,'use_qk_l2norm_in_kernel':norm}
            a=baseline(q,k,v,**kwargs);b=optimized(q,k,v,**kwargs)
            assert torch.equal(a[0],b[0])and ((a[1]is None and b[1]is None)or torch.equal(a[1],b[1]))
            cases.append({'device':device,'sequence':n,'heads':h,'key_dim':d,'value_dim':v.shape[-1],'qk_normalization':norm,'initial_and_final_state':state,'chunk_size':chunk,'full_output_and_state_bitwise_equal':True})
    return cases

def capture_three(engine,body,root,expected,code,torch,save,mlp_code=None):
    root.mkdir();original_apply=engine.processor.apply_chat_template;original_generate=engine.model.generate
    prepared={};first={};logits=[];counts={'patched_or_baseline_kernel_calls':0,'actual_MLP_calls':0};seen=[False]
    def apply(*args,**kwargs):
        value=original_apply(*args,**kwargs)
        for k,v in value.items():
            prepared[k]=tensor(torch,v,root/('prepared_'+k+'.tensor'))
            assert all(prepared[k][f]==expected[k][f]for f in ['shape','dtype','bytes','sha256']),k
        save(root/'prepared.json',prepared);return value
    def hook(_module,args,kwargs):
        if seen[0]:return
        seen[0]=True
        for k in prepared:
            first[k]=tensor(torch,kwargs[k],root/('first_forward_'+k+'.tensor'),root/prepared[k]['file'])
            assert all(first[k][f]==prepared[k][f]for f in ['shape','dtype','bytes','sha256'])
        save(root/'first-forward.json',first)
    def generate(*args,**kwargs):
        assert not args and kwargs['generation_config'].max_new_tokens==3
        save(root/'effective-generation.json',kwargs['generation_config'].to_dict())
        result=original_generate(**kwargs,return_dict_in_generate=True,output_logits=True)
        for i,v in enumerate(result.logits):logits.append(tensor(torch,v,root/('full-logits-'+str(i)+'.tensor')))
        tensor(torch,result.sequences,root/'sequence_ids.tensor')
        return result.sequences
    def profile(frame,event,arg):
        if event=='call'and frame.f_code is code:counts['patched_or_baseline_kernel_calls']+=1
        if event=='call'and frame.f_code is mlp_code:counts['actual_MLP_calls']+=1
    engine.processor.apply_chat_template=apply;engine.model.generate=generate
    handle=engine.model.register_forward_pre_hook(hook,with_kwargs=True)
    expected_engineering_cap=False
    try:
        sys.setprofile(profile)
        try:engine.generate(body['messages'],3,root/'native-call.json',original_body=body)
        except RuntimeError as exc:
            if str(exc)!='Output cap hit; preserve incomplete attempt':raise
            expected_engineering_cap=True
    finally:
        sys.setprofile(None);handle.remove();engine.processor.apply_chat_template=original_apply;engine.model.generate=original_generate
        torch.cuda.empty_cache()
    native=json.loads((root/'native-call.json').read_bytes())
    assert len(native['generated_ids'])==3 and len(logits)==3 and counts['patched_or_baseline_kernel_calls']==48
    assert counts['actual_MLP_calls']==192
    save(root/'invariance-record.json',{'engineering_cap_3_expected':expected_engineering_cap,'not_a_formal_EOS_trial':True,'full_vocab_logits':logits,'generated_ids':native['generated_ids'],'actual_original_or_optimized_chunk_kernel_calls':counts['patched_or_baseline_kernel_calls'],'input_tokens':prepared['input_ids']['shape'][-1],'actual_MLP_calls':counts['actual_MLP_calls']})
    return {'generated_ids':native['generated_ids'],'full_vocab_logits':logits,'kernel_calls':counts['patched_or_baseline_kernel_calls'],'input_tokens':prepared['input_ids']['shape'][-1],'actual_MLP_calls':counts['actual_MLP_calls']}

def install_validated(native,package,root,body,expected,save,sha,resource):
    torch=native.torch;engine=native.engine
    module=sys.modules[type(engine.model).__module__];raw=inspect.unwrap(module.torch_chunk_gated_delta_rule)
    original_code=raw.__code__;original_source=inspect.getsource(raw)
    source_path=package/'torch_chunk_lifetime.py';source=source_path.read_text()
    original_ast=arithmetic_ast(original_source);optimized_ast=arithmetic_ast(source)
    assert original_ast==optimized_ast,'Numerical AST changed; reject memory-only repair'
    namespace=dict(raw.__globals__);exec(compile(source,str(source_path),'exec'),namespace)
    candidate=namespace['torch_chunk_gated_delta_rule']
    assert not original_code.co_freevars and not candidate.__code__.co_freevars
    baseline=types.FunctionType(original_code,raw.__globals__,raw.__name__,raw.__defaults__);baseline.__kwdefaults__=copy.deepcopy(raw.__kwdefaults__)
    optimized=types.FunctionType(candidate.__code__,raw.__globals__,raw.__name__,raw.__defaults__);optimized.__kwdefaults__=copy.deepcopy(raw.__kwdefaults__)
    proof={'source_native_module_sha256':sha(Path(module.__file__)),'repair_source_sha256':sha(source_path),'arithmetic_AST_sha256':hashlib.sha256(original_ast.encode()).hexdigest(),'all_numerical_AST_nodes_unchanged':True,'only_dead_local_deletions_added':True,'weights_precision_attention_kernel_and_reduction_order_unchanged':True,'pinned_native_source_file_modified':False}
    from mlp_lifetime import prepare
    mlp,mlp_original_code,mlp_candidate_code,mlp_proof=prepare(torch,module,engine.model,root,save,sha)
    proof['arithmetic_AST_scope']='chunk delta core only; MLP buffer reuse separately source-bound and bitwise tested'
    proof['MLP_memory_proof']=mlp_proof
    save(root/'source-proof.json',proof)
    resource(True)
    cases=run_kernel_tests(torch,baseline,optimized,engine.model.config.text_config)
    save(root/'kernel-bitwise-tests.json',cases)
    resource(True)
    before=capture_three(engine,body,root/'baseline-three-cached-steps',expected,original_code,torch,save,mlp_original_code)
    raw.__code__=candidate.__code__
    mlp.__code__=mlp_candidate_code
    try:
        resource(True)
        after=capture_three(engine,body,root/'optimized-three-cached-steps',expected,candidate.__code__,torch,save,mlp_candidate_code)
        assert before['generated_ids']==after['generated_ids']
        for a,b in zip(before['full_vocab_logits'],after['full_vocab_logits']):
            assert all(a[k]==b[k]for k in ['shape','dtype','bytes','sha256'])
        result={**proof,'kernel_tests':len(cases),'all_kernel_tests_bitwise_equal':True,'full_model_cached_steps':3,'all_full_vocab_logits_and_sequence_ids_bitwise_equal':True,'real_model_input_tokens':before['input_tokens'],'real_model_images':15,'actual_capacity_model_generate_calls':2,'actual_chunk_calls_per_pass':48,'actual_MLP_calls_per_pass':192,'engineering_max_new_tokens':3,'formal_actor_cap_unchanged':2048,'all_future_inputs_bitwise_identity_claimed':False,'installed':True,'time':time.time()}
        save(root/'result.json',result)
        return result
    except BaseException:
        raw.__code__=original_code
        mlp.__code__=mlp_original_code
        raise
