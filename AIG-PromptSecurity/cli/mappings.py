# 支持的scenarios和techniques映射
TECHNIQUE_CLASS_MAP = {
    "Base64": "deepteam.attacks.single_turn.Base64",
    "Braille": "deepteam.attacks.single_turn.Braille",
    "Ecoji": "deepteam.attacks.single_turn.Ecoji",
    "Emoji": "deepteam.attacks.single_turn.Emoji",
    "GrayBox": "deepteam.attacks.single_turn.GrayBox",
    "Homomorphic": "deepteam.attacks.single_turn.Homomorphic",
    "ICRTJailbreak": "deepteam.attacks.single_turn.ICRTJailbreak",
    "Leetspeak": "deepteam.attacks.single_turn.Leetspeak",
    "MathProblem": "deepteam.attacks.single_turn.MathProblem",
    "Morse": "deepteam.attacks.single_turn.Morse",
    "Multilingual": "deepteam.attacks.single_turn.Multilingual",
    "Nato": "deepteam.attacks.single_turn.Nato",
    "PromptInjection": "deepteam.attacks.single_turn.PromptInjection",
    "PromptProbing": "deepteam.attacks.single_turn.PromptProbing",
    "Raw": "deepteam.attacks.single_turn.Raw",
    "Roleplay": "deepteam.attacks.single_turn.Roleplay",
    "Rot13": "deepteam.attacks.single_turn.ROT13",
    "Zalgo": "deepteam.attacks.single_turn.Zalgo",
    "Zerowidth": "deepteam.attacks.single_turn.Zerowidth",
    "BadLikertJudge": "deepteam.attacks.multi_turn.BadLikertJudge",
    "BestofN": "deepteam.attacks.multi_turn.BestofN",
    "CrescendoJailbreaking": "deepteam.attacks.multi_turn.CrescendoJailbreaking",
    "LinearJailbreaking": "deepteam.attacks.multi_turn.LinearJailbreaking",
    "SequentialJailbreak": "deepteam.attacks.multi_turn.SequentialJailbreak",
    "TreeJailbreaking": "deepteam.attacks.multi_turn.TreeJailbreaking",
}

SCENARIO_CLASS_MAP = {
    "Bias": "deepteam.vulnerabilities.Bias",
    "Toxicity": "deepteam.vulnerabilities.Toxicity",
    "Misinformation": "deepteam.vulnerabilities.Misinformation",
    "IllegalActivity": "deepteam.vulnerabilities.IllegalActivity",
    "PromptLeakage": "deepteam.vulnerabilities.PromptLeakage",
    "PIILeakage": "deepteam.vulnerabilities.PIILeakage",
    "UnauthorizedAccess": "deepteam.vulnerabilities.UnauthorizedAccess",
    "ExcessiveAgency": "deepteam.vulnerabilities.ExcessiveAgency",
    "Robustness": "deepteam.vulnerabilities.Robustness",
    "IntellectualProperty": "deepteam.vulnerabilities.IntellectualProperty",
    "Competition": "deepteam.vulnerabilities.Competition",
    "GraphicContent": "deepteam.vulnerabilities.GraphicContent",
    "PersonalSafety": "deepteam.vulnerabilities.PersonalSafety",
    "Custom": "deepteam.vulnerabilities.CustomVulnerability",
    "CustomPrompt": "deepteam.vulnerabilities.CustomPrompt",
    "MultiDataset": "deepteam.vulnerabilities.MultiDatasetVulnerability",
}

# 支持的自定义metric映射
METRIC_CLASS_MAP = {
    'RandomMetric': 'deepteam.metrics.RandomMetric',
    'JailbreakMetric': 'deepteam.metrics.JailbreakMetric'
} 
