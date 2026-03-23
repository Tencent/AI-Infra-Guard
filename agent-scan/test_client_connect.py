import argparse
from utils.aig_logger import scanLogger
from core.agent_adapter.adapter import AIProviderClient, ProviderTestResult

parser = argparse.ArgumentParser(description="Agent CLI Runner")
parser.add_argument("--client_file", type=str, help="Client config file")
parser.add_argument("--prompt", type=str, default="Only return 1", help="Client config file")
args = parser.parse_args()


def is_client_connect(file_path: str, prompt: str):
    client = AIProviderClient()
    agent_provider = client.load_config_from_file(file_path)[0]
    try:
        response = client.call_provider(agent_provider, prompt)
    except Exception as e:
        # 获取堆栈信息 Unresolved reference 'traceback'
        import traceback
        traceback = traceback.format_exc()
        response = ProviderTestResult(
            success=False,
            message=f"Error during execution: {e}\n{traceback}",
        )
    scanLogger.result_update(content=response.model_dump())
    return response


if __name__ == "__main__":
    res = is_client_connect(args.client_file, args.prompt)
