from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from ..utils.context import ContextManager
from ..utils.errors import StepInputError, StepOutputError
from ..utils.progress_tracker import ProgressTracker


class BaseStep(ABC):
    def __init__(
        self,
        name: str,
        input_files: List[str],
        output_files: List[str],
        progress_tracker: Optional[ProgressTracker],
        context_manager: ContextManager
    ):
        self.name = name
        self.input_files = input_files
        self.output_files = output_files
        self.progress_tracker = progress_tracker
        self.context_manager = context_manager
        
    def execute(self) -> Dict:
        """执行步骤"""
        # 验证输入
        missing_inputs = self._validate_inputs(self.context_manager)
        if missing_inputs:
            raise StepInputError(self.name, missing_inputs)
            
        # 执行步骤
        result = self._execute(self.context_manager)
        
        # 验证输出
        if not self._validate_outputs(result):
            raise StepOutputError(self.name, "步骤输出不完整")
            
        return result
        
    def _validate_inputs(self, context_manager: ContextManager) -> List[str]:
        """验证输入数据"""
        return context_manager.validate_keys(self.input_files)
        
    def _validate_outputs(self, result: Dict) -> bool:
        """验证输出数据"""
        return all(output_file in result for output_file in self.output_files)
    
    @abstractmethod
    def _execute(self, context_manager: ContextManager) -> Dict:
        """具体步骤实现"""
        pass
