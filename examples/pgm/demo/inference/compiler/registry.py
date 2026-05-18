from ..kernels import ExactKernelFamily, HilbertKernelFamily
from ..kernels.base import KernelFamily


class Registry:
    def __init__(self, kernel_families: list[KernelFamily]) -> None:
        self.kernel_families = list(kernel_families)


def default_registry() -> Registry:
    return Registry([ExactKernelFamily(), HilbertKernelFamily()])
