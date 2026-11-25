"""Pure boundary policy used by the separately authorized dual-GPU launcher."""

def resource_reasons(gpus, processes, lease_owners, expected_uid=1015):
    reasons=[]
    if set(gpus)!={1,3}:
        return ['Expected exactly physical GPU1 and GPU3']
    for gpu in [3,1]:
        row=gpus[gpu]
        if row.get('query_ok') is not True:
            reasons.append('GPU%d resource query is incomplete'%gpu)
        if not isinstance(row.get('free_mib'),int) or row['free_mib']<=23500:
            reasons.append('GPU%d lacks required23500MiB free headroom'%gpu)
        if lease_owners.get(gpu)!=expected_uid:
            reasons.append('GPU%d task lock is not owned by the expected UID'%gpu)
        if any(p.get('physical_gpu')==gpu for p in processes):
            reasons.append('GPU%d has an existing compute process; sharing/preemption forbidden'%gpu)
    return reasons
