from deepteam import red_team
from deepteam.vulnerabilities import *
from deepteam.attacks.single_turn import PromptInjection, Base64
from deepteam.attacks.multi_turn import LinearJailbreaking


async def model_callback(input: str) -> str:
    # Replace this with your LLM application
    return f"I'm sorry but I can't answer this: {input}"


pii_leakage = PIILeakage(
    types=[
        "direct disclosure",
        "api and database access",
        "session leak",
        "social manipulation",
    ]
)
prompt_leakage = PromptLeakage(
    types=[
        "secrets and credentials",
        "guard exposure",
        "instructions",
        "permissions and roles",
    ]
)


bias = Bias(types=["race", "gender", "politics", "religion"])

# bias = Bias(types=["race"])


toxicity = Toxicity(types=["insults", "mockery", "profanity", "threats"])


unauthorized_access = UnauthorizedAccess(
    types=[
        "rbac",
        "bfla",
        "bola",
        "debug access",
        "shell injection",
        "sql injection",
        "ssrf",
    ]
)

misinformation = Misinformation(
    types=[
        "factual errors",
        "unsupported claims",
        "expertize misrepresentation",
    ]
)

intellectual_property = IntellectualProperty(
    types=[
        "copyright violations",
        "trademark infringement",
        "patent disclosure",
        "imitation",
    ]
)

excessive_agency = ExcessiveAgency(
    types=["functionality", "permissions", "autonomy"]
)

robustness = Robustness(types=["hijacking", "input overreliance"])

competition = Competition(
    types=[
        "competitor mention",
        "market manipulation",
        "confidential strategies",
        "discreditation",
    ]
)

illegal_activity = IllegalActivity(
    types=[
        "violent crimes",
        "child exploitation",
        "cybercrime",
        "illegal drugs",
        "non violent crimes",
        "sex crimes",
        "weapons",
    ]
)

graphic_content = GraphicContent(
    types=["sexual content", "graphic content", "pornographic content"]
)

personal_safety = PersonalSafety(
    types=[
        "bullying",
        "dangerous challenges",
        "self-harm",
        "stalking",
        "unsafe practices",
    ]
)

prompt_injection = PromptInjection()
j = LinearJailbreaking()

api_security = CustomVulnerability(
    name="API Security",  # Name reflecting the security concern
    types=["endpoint_exposure", "auth_bypass"],  # Specific aspects to test
)

red_team(
    model_callback=model_callback,
    vulnerabilities=[
        bias,
        toxicity,
        unauthorized_access,
        # misinformation,
        # pii_leakage,
        # prompt_leakage,
        # intellectual_property,
        # excessive_agency,
        # robustness,
        # competition,
        # illegal_activity,
        # graphic_content,
        # personal_safety
    ],
    attacks=[prompt_injection, Base64()],
    ignore_errors=True,
)

# from deepteam import red_team
# from deepteam.vulnerabilities import Bias
# from deepteam.attacks.single_turn import PromptInjection


# async def model_callback(input: str) -> str:
#     # Replace this with your LLM application
#     return f"I'm sorry but I can't answer this: {input}"


# bias = Bias(types=["race"])
# prompt_injection = PromptInjection()

# red_team(
#     model_callback=model_callback,
#     vulnerabilities=[bias],
#     attacks=[prompt_injection],
# )
