# 支持的scenarios和techniques映射
TECHNIQUE_CLASS_MAP = {
    "Raw": "deepteam.attacks.single_turn.Raw",
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
