def connectivity(default_client, config_file: str) -> bool:
    default_prompt = "Only return 1"
    providers = default_client.load_config_from_file(config_file)
    result = default_client.call_provider(providers[0], default_prompt)
    return result.success
