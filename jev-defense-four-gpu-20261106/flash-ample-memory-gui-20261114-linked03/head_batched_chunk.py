def torch_chunk_gated_delta_rule(
    query,
    key,
    value,
    g,
    beta,
    chunk_size=64,
    initial_state=None,
    output_final_state=False,
    use_qk_l2norm_in_kernel=False,
    **kwargs,
):
    outputs = []
    states = []
    heads = query.shape[2]
    for start in range(0, heads, 12):
        end = min(start + 12, heads)
        part, state = _mirage_lifetime_chunk_core(
            query[:, :, start:end],
            key[:, :, start:end],
            value[:, :, start:end],
            g=g[:, :, start:end],
            beta=beta[:, :, start:end],
            chunk_size=chunk_size,
            initial_state=None if initial_state is None else initial_state[:, start:end],
            output_final_state=output_final_state,
            use_qk_l2norm_in_kernel=use_qk_l2norm_in_kernel,
            **kwargs,
        )
        outputs.append(part)
        if output_final_state:
            states.append(state)
    return torch.cat(outputs, dim=2), torch.cat(states, dim=1) if output_final_state else None
