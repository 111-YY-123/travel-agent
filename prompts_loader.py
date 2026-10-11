from utils.path_tool import get_abs_path


def _load(path: str) -> str:
    full_path = get_abs_path(path)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"提示词文件缺失：{full_path}\n"
            f"请检查 prompts/ 目录下是否有该文件。"
        )
    except Exception as e:
        raise RuntimeError(f"加载提示词失败：{full_path}，错误：{e}")


SUPERVISOR_PROMPT = _load("prompts/supervisor_prompts.txt")
FOOD_PROMPT = _load("prompts/food_prompts.txt")
NATURE_PROMPT = _load("prompts/nature_prompts.txt")
CULTURE_PROMPT = _load("prompts/culture_prompts.txt")
BUSINESS_PROMPT = _load("prompts/business_prompts.txt")
SYNTHESIZER_PROMPT = _load("prompts/synthesizer_prompts.txt")
ACCOMMODATION_PROMPT = _load("prompts/accommodation_prompts.txt")
TRANSPORT_PROMPT = _load("prompts/transport_prompts.txt")
FINALIZER_PROMPT = _load("prompts/finalizer_prompts.txt")