from typing import Optional

class TaskError(Exception):
    """任务处理基础异常"""
    def __init__(self, message: str, step_name: Optional[str] = None):
        self.message = message
        self.step_name = step_name
        super().__init__(message)

class StepExecutionError(TaskError):
    """步骤执行异常"""
    def __init__(self, step_name: str, original_error: Exception):
        self.original_error = original_error
        super().__init__(
            f"步骤 {step_name} 执行失败: {str(original_error)}", 
            step_name
        )

class StepInputError(TaskError):
    """步骤输入异常"""
    def __init__(self, step_name: str, missing_inputs: list):
        super().__init__(
            f"步骤 {step_name} 缺少输入: {', '.join(missing_inputs)}", 
            step_name
        )

class StepOutputError(TaskError):
    """步骤输出异常"""
    def __init__(self, step_name: str, message: str):
        super().__init__(
            f"步骤 {step_name} 输出错误: {message}", 
            step_name
        )
