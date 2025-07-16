from deepteam.attacks.multi_turn import LinearJailbreaking
from deepteam.vulnerabilities import Bias
from deepteam import red_team


async def model_callback(input: str) -> str:
    # Replace this with your LLM application
    return f"I'm sorry but I can't answer this: {input}"


linear_jailbreaking = LinearJailbreaking()
red_team(
    attacks=[linear_jailbreaking],
    model_callback=model_callback,
    vulnerabilities=[Bias(types=["gender"])],
)
