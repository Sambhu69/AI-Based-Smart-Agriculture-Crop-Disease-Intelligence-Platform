import sys
import torch

def check_gpu():
    print("=" * 50)
    print("PyTorch & GPU Diagnostics")
    print("=" * 50)
    print(f"Python version : {sys.version.split()[0]}")
    print(f"PyTorch version: {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available : {cuda_available}")
    
    if cuda_available:
        print(f"CUDA Version   : {torch.version.cuda}")
        device_count = torch.cuda.device_count()
        print(f"Device Count   : {device_count}")
        for i in range(device_count):
            device_name = torch.cuda.get_device_name(i)
            mem_gb = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
            print(f"  [{i}] {device_name} ({mem_gb:.2f} GB VRAM)")
            
        # Run test tensor computation on GPU
        x = torch.rand(1000, 1000, device="cuda")
        y = torch.matmul(x, x)
        print("Tensor computation on GPU: SUCCESS!")
    else:
        print("No CUDA-compatible GPU detected by PyTorch (running in CPU mode).")
    print("=" * 50)

if __name__ == "__main__":
    check_gpu()