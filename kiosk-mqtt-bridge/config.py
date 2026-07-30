import sys
import tomllib

CONFIG_PATH = "config.toml"

def load_config():
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Error loading config from {CONFIG_PATH}: {e}", file=sys.stderr)
        sys.exit(1)

def update_config_url(new_url):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines):
            if line.strip().startswith("default_url"):
                lines[i] = f'default_url = "{new_url}"\n'
                break
                
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return True
    except Exception as e:
        print(f"Error updating config.toml: {e}", file=sys.stderr)
        return False
