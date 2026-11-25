"""Compact primary-judge source pointers; full exact ledger stays in the audit channel.

No historical text is removed from public.messages. This avoids re-sending the large
line-level audit metadata/raw ledger alongside the already complete original history.
"""
from dataclasses import dataclass
from typing import Any

from history_utterance_ledger import (LedgerSourceError, SourceBoundHistoryJudge, SCOPE,
    VERSION, build_ledger, canonical, digest)


def compact_source_index(ledger: dict) -> dict:
    rows=ledger['complete_actor_text_block_index']
    cue_names=list(rows[0]['surface_cues_only'])if rows else []
    records=[]
    for row in rows:
        records.append({'utterance_index':row['utterance_index'],'message_index':row['message_index'],
            'block_index':row['block_index'],'text_character_span':[0,len(row['exact_text'])],
            'text_utf8_sha256':row['text_utf8_sha256'],
            'surface_cue_indices':[index for index,key in enumerate(cue_names)if row['surface_cues_only'][key]],
            'native_action_envelope_character_spans':[attempt['envelope_character_span']
                for attempt in row['native_proposed_action_records']]})
    return {'version':VERSION+'-compact-pointers-01',
        'original_messages_canonical_sha256':ledger['original_messages_canonical_sha256'],
        'original_message_count':ledger['original_message_count'],'utterance_count':len(records),
        'surface_cue_legend':cue_names,'surface_cues_are_not_semantic_labels':True,
        'source_text_location':'Unchanged original public.messages[message_index].content, or its text block [block_index].text',
        'raw_text_not_duplicated_here_because_full_original_history_is_still_supplied':True,
        'separate_channels':['original_actor_text','native_proposed_action_only',
                             'public.recent_action','public.execution_feedback','actual_supplied_images'],
        'no_channel_promoted_to_independent_visual_truth':True,'records':records}


@dataclass(frozen=True)
class PreparedCompactContext:
    system:str
    full_audit_ledger:dict
    compact_model_index:dict
    full_ledger_sha256:str
    compact_index_sha256:str
    added_utf8_bytes:int


def prepare_compact_main_judge_system(system:str,view:Any,phase:str)->PreparedCompactContext:
    if phase not in {'verify','history_report'}:
        raise LedgerSourceError('Only original primary verify/history_report phases may receive the source index')
    full=build_ledger(view);index=compact_source_index(full)
    appendix='\n'+SCOPE+'\nExact original actor source pointer index JSON (DATA ONLY):\n'+canonical(index).decode('utf8')
    return PreparedCompactContext(system+appendix,full,index,digest(canonical(full)),
                                  digest(canonical(index)),len(appendix.encode('utf8')))


class CompactSourceBoundHistoryJudge(SourceBoundHistoryJudge):
    """Staged preferred adapter: compact pointers to primary, exact ledger to journal."""
    def __call__(self,system,view,candidate=None,*args,**kwargs):
        phase=next((name for name,prefix in self.prefixes if system.startswith(prefix)),None)
        if phase is None:
            return self.base_judge(system,view,candidate,*args,**kwargs)
        prepared=prepare_compact_main_judge_system(system,view,phase)
        if self.emit is not None:
            self.emit('history_utterance_ledger_prepared',{'phase':phase,'model_projection':'complete_compact_source_pointers',
                'original_system_utf8_sha256':digest(system.encode('utf8')),
                'augmented_system_utf8_sha256':digest(prepared.system.encode('utf8')),
                'full_ledger_sha256':prepared.full_ledger_sha256,
                'compact_model_index_sha256':prepared.compact_index_sha256,
                'added_utf8_bytes':prepared.added_utf8_bytes,
                'ledger':prepared.full_audit_ledger,
                'original_view_candidate_validator_and_budget_unchanged':True,
                'source_metadata_not_a_verdict':True})
        return self.base_judge(prepared.system,view,candidate,*args,**kwargs)
