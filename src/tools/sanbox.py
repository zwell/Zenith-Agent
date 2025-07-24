from langchain.tools import tool
from e2b import AsyncSandbox

# --- 1. 沙箱工具管理器 (保持不变，这是我们的核心模块) ---
class SandboxToolManager:
    def __init__(self, sandbox_instance: AsyncSandbox):
        self.sandbox = sandbox_instance

    @tool
    async def run_shell_command(self, command: str) -> str:
        """Executes a shell command in a secure sandboxed environment..."""
        # ... (省略具体实现, 和上一条回复一样) ...
        print(f"--- Sandbox: Executing shell command: {command} ---")
        process = await self.sandbox.process.start(command)
        await process.wait()
        return f"STDOUT:\n{process.output.stdout}\nSTDERR:\n{process.output.stderr}"


    @tool
    async def write_file_in_sandbox(self, filepath: str, content: str) -> str:
        """Writes content to a file inside the sandboxed environment..."""
        # ... (省略具体实现) ...
        print(f"--- Sandbox: Writing to file: {filepath} ---")
        await self.sandbox.filesystem.write(filepath, content)
        return f"Successfully wrote to {filepath}."


    @tool
    async def read_file_in_sandbox(self, filepath: str) -> str:
        """Reads the content of a file from the sandboxed environment..."""
        # ... (省略具体实现) ...
        print(f"--- Sandbox: Reading from file: {filepath} ---")
        return await self.sandbox.filesystem.read(filepath)


    def get_all_tools(self):
        return [
            self.run_shell_command,
            self.write_file_in_sandbox,
            self.read_file_in_sandbox,
        ]