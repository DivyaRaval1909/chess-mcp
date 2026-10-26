import torch


if torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

print("PyTorch version:", torch.__version__)
print("Training device:", device)

test_tensor = torch.rand(2, 3, device=device)
print("Tensor created successfully:")
print(test_tensor)