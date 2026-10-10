"""Opt-in unsafe tools. Do not enable for untrusted models or users."""
import os, subprocess, sys, tempfile
from .common import safe_path

def register(mcp):
    @mcp.tool()
    def terminal_run(command: str, confirm: bool = False) -> str:
        """Run a shell command only when unsafe tools are enabled and confirm=true."""
        if not confirm: return "Command not run. Set confirm=true after reviewing it."
        # Explicit opt-in is already required by server.py. This still has host-level privileges.
        result = subprocess.run(command, shell=True, cwd=str(safe_path(".")),
                                capture_output=True, text=True, timeout=30)
        return f"exit={result.returncode}\nSTDOUT:\n{result.stdout[:10000]}\nSTDERR:\n{result.stderr[:5000]}"

    @mcp.tool()
    def python_run(code: str, confirm: bool = False) -> str:
        """Execute Python code in a subprocess. Disabled unless FACTORY_OS_ENABLE_UNSAFE_TOOLS=true and confirm=true."""
        if not confirm:
            return "Python code not run. Review it and call again with confirm=true."
        if len(code) > 20000:
            raise ValueError("Code is too large (maximum 20000 characters).")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False, dir=str(safe_path("."))) as f:
            f.write(code)
            script = f.name
        try:
            result = subprocess.run([sys.executable, script], cwd=str(safe_path(".")), capture_output=True, text=True, timeout=30)
            return f"exit={result.returncode}\nSTDOUT:\n{result.stdout[:10000]}\nSTDERR:\n{result.stderr[:5000]}"
        finally:
            try: os.remove(script)
            except OSError: pass
