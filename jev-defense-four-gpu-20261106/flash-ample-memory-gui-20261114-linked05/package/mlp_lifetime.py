"""Reuse an unaliased native SiLU result for the identical elementwise product."""
import ast,hashlib,inspect,time,types
from pathlib import Path

def forward(self,x):
    gate=self.act_fn(self.gate_proj(x))
    up=self.up_proj(x)
    gate.mul_(up)
    del up
    return self.down_proj(gate)

def prepare(torch,module,model,root,save,sha):
    from memory_lifetime import tensor
    cls=module.Qwen3_5MLP;raw=cls.forward
    original=inspect.getsource(raw)
    expected='def forward(self, x):\n    down_proj = self.down_proj(self.act_fn(self.gate_proj(x)) * self.up_proj(x))\n    return down_proj\n'
    import textwrap
    assert ast.dump(ast.parse(textwrap.dedent(original)),include_attributes=False)==ast.dump(ast.parse(expected),include_attributes=False)
    assert model.config.text_config.hidden_act=='silu'
    assert not raw.__code__.co_freevars and not forward.__code__.co_freevars
    baseline=types.FunctionType(raw.__code__,raw.__globals__,raw.__name__,raw.__defaults__)
    candidate=types.FunctionType(forward.__code__,raw.__globals__,raw.__name__,raw.__defaults__)
    modules=[m for m in model.modules()if isinstance(m,cls)];assert len(modules)==64
    by_device={}
    for layer in modules:by_device.setdefault(str(layer.gate_proj.weight.device),layer)
    rows=[]
    with torch.inference_mode():
        for device,layer in by_device.items():
            for n in [1,65]:
                torch.manual_seed(871+n)
                x=torch.randn(1,n,layer.hidden_size,device=device,dtype=torch.bfloat16)*0.01
                target=root/('mlp-'+device.replace(':','-')+'-'+str(n));target.mkdir()
                before=tensor(torch,x,target/'input.tensor')
                a=baseline(layer,x);ar=tensor(torch,a,target/'native-output.tensor');del a
                b=candidate(layer,x);br=tensor(torch,b,target/'reuse-output.tensor');del b
                unchanged=tensor(torch,x,target/'input-after.tensor')
                row={'device':device,'sequence':n,'hidden_size':layer.hidden_size,'intermediate_size':layer.intermediate_size,'input':before,'native_output':ar,'reuse_output':br,'input_after':unchanged,'full_output_bitwise_equal':ar['sha256']==br['sha256'],'input_not_mutated':before['sha256']==unchanged['sha256']}
                save(target/'result.json',row);rows.append(row)
                assert row['full_output_bitwise_equal']and row['input_not_mutated']
    proof={'source_native_MLP_sha256':hashlib.sha256(original.encode()).hexdigest(),'memory_MLP_source_sha256':sha(Path(__file__)),'original_expression_bound':True,'original_linear_and_silu_operations_retained':True,'only_elementwise_product_destination_reuses_dead_SiLU_buffer':True,'input_or_weights_not_modified':True,'original_MLP_AST_identity_claimed':False,'actual_weight_GPU_output_bitwise_tests':len(rows),'actual_devices':list(by_device),'all_tests_passed':True,'pinned_native_source_modified':False,'time':time.time()}
    save(root/'mlp-memory-proof.json',proof)
    return raw,raw.__code__,forward.__code__,proof
