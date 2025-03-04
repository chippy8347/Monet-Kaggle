import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import tensorflow_addons as tfa

from kaggle_datasets import KaggleDatasets
import matplotlib.pyplot as plt
import numpy as np

try:
    tpu = tf.distribute.cluster_resolver.TPUClusterResolver()
    print('Device:', tpu.master())
    tf.config.experimental_connect_to_cluster(tpu)
    tf.tpu.experimental.initialize_tpu_system(tpu)
    strategy = tf.distribute.experimental.TPUStrategy(tpu)
except:
    strategy = tf.distribute.get_strategy()
print('Number of replicas:', strategy.num_replicas_in_sync)

AUTOTUNE = tf.data.experimental.AUTOTUNE
    
print(tf.__version__)
#Device: grpc://10.0.0.2:84# -*- coding: utf-8 -*-
"""4620-Group8-Initial.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/18XCC_PAJH-El5PUlV8FQwbQD8_82T6ju

# Introduction

Import Libraries
"""

import torch
import torch.nn as nn
import torch.optim as optim
import torchvision
from torchvision import datasets, transforms
import torchvision.transforms as transforms
from torch.utils.data import DataLoader, Dataset
import torch.nn.functional as F
import matplotlib.pyplot as plt
import numpy as np
import os
from PIL import Image

"""Install datasets (requires kaggle.json) [Only do once!]"""

!pip install kaggle
!mkdir -p ~/.kaggle
!cp kaggle.json ~/.kaggle/
!chmod 600 ~/.kaggle/kaggle.json

!kaggle competitions download -c gan-getting-started
!unzip gan-getting-started.zip

"""### Create Dataset Class"""

# Define paths
photo_jpg_path = "/content/photo_jpg"
monet_jpg_path = "/content/monet_jpg"

# Custom dataset class
class CustomImageDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        #connects to the directory
        self.root_dir = root_dir
        self.transform = transform
        self.image_files = [f for f in os.listdir(root_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_path = os.path.join(self.root_dir, self.image_files[idx])
        image = Image.open(img_path).convert('RGB')
        if self.transform:
            image = self.transform(image)
        return image

# Define transformations
transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # Scale to [-1, 1]
])

# Load datasets
photo_jpg_dataset = CustomImageDataset(root_dir=photo_jpg_path, transform=transform)
monet_jpg_dataset = CustomImageDataset(root_dir=monet_jpg_path, transform=transform)

# Create dataloaders
photo_jpg_loader = DataLoader(photo_jpg_dataset, batch_size=1, shuffle=False)
monet_jpg_loader = DataLoader(monet_jpg_dataset, batch_size=1, shuffle=False)

# Function to convert tensor to image for visualization
def tensor_to_image(tensor):
    """
    Converts a normalized tensor to a PIL image.
    Args:
        tensor: A tensor in the range [-1, 1].
    Returns:
        A numpy array in the range [0, 1].
    """
    tensor = tensor.squeeze(0)  # Remove batch dimension
    tensor = tensor.permute(1, 2, 0)  # Change shape from (C, H, W) to (H, W, C)
    image = tensor * 0.5 + 0.5  # Rescale to [0, 1]
    return image.numpy()

# Get one example from each dataset
example_photo = next(iter(photo_jpg_loader))
example_monet = next(iter(monet_jpg_loader))

# Visualize the examples
plt.figure(figsize=(10, 5))

# Photo example
plt.subplot(121)
plt.title('Photo (JPG)')
plt.imshow(tensor_to_image(example_photo))

# Monet example
plt.subplot(122)
plt.title('Monet (JPG)')
plt.imshow(tensor_to_image(example_monet))

plt.show()

"""# Generator Model

### Overview:

- The generator starts off with random noise and gradually upscales it to the required size (256x256) to create an image.
- Each layer will double the image size and reducing the feature maps.
- The final layer produces a 3-channel RGB image.
- Pixel values are scaled between -1 and 1.
"""

# Image-to-Image (IRL-to-Monet) Generator

# Take an image
# Downsample the upsample

class Generator(nn.Module):
  def __init__(self, img_channels=3, feature_maps=64):
    super(Generator, self).__init__()

    # downsampling
    # reduce the spacial dimensions and increase the depth (features)
    self.down1 = self.conv_block(img_channels, feature_maps, kernel_size=7, stride=1)
    self.down2 = self.conv_block(feature_maps, feature_maps * 2, kernel_size=3, stride=2)
    self.down3 = self.conv_block(feature_maps * 2, feature_maps * 4, kernel_size=3, stride=2)

    # residual blocks
    # preserve and refine the details while maintaining the desired img style
    self.res_blocks = nn.Sequential(
        *[self.residual_block(feature_maps * 4) for _ in range(6)])
    # this refines things like "brush strokes" and retains integrity of the image

    # upsampling
    # convert the 256x64x64 feature maps back to 3x256x256
    self.up1 = self.upconv_block(feature_maps * 4, feature_maps * 2)
    self.up2 = self.upconv_block(feature_maps * 2, feature_maps)
    self.up3 = nn.Conv2d(feature_maps, img_channels, kernel_size=7, stride=1, padding=3)
    # normalize the output to match real Monet paintings for more
    # efficient learning
    self.tanh = nn.Tanh()

  def conv_block(self, in_channels, out_channels, kernel_size, stride):
      return nn.Sequential(
          nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding=1),
          nn.ReLU(inplace=True),
          nn.InstanceNorm2d(out_channels)
      )

  def upconv_block(self, in_channels, out_channels):
      return nn.Sequential(
          nn.ConvTranspose2d(in_channels, out_channels, kernel_size=3, stride=2, padding=1, output_padding=1),
          nn.ReLU(inplace=True),
          nn.InstanceNorm2d(out_channels)
      )

  def residual_block(self, in_channels):
      return nn.Sequential(
          nn.Conv2d(in_channels, in_channels, kernel_size=3, stride=1, padding=1),
          nn.InstanceNorm2d(in_channels),
          nn.ReLU(inplace=True),
          nn.Conv2d(in_channels, in_channels, kernel_size=3, stride=1, padding=1),
          nn.InstanceNorm2d(in_channels),
      )

  def forward(self, x):
      x = self.down1(x)
      x = self.down2(x)
      x = self.down3(x)
      x = self.res_blocks(x)
      x = self.up1(x)
      x = self.up2(x)
      x = self.up3(x)
      x = self.tanh(x)
      return x

"""### Test with a real photo:"""

generator = Generator()

# Assuming `generator` is our trained model
generator.eval()  # Set to evaluation mode

# Get one real photo sample
example_photo = next(iter(photo_jpg_loader))

# Move to GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
generator.to(device)
example_photo = example_photo.to(device)

# Pass through the generator
with torch.no_grad():
    generated_monet = generator(example_photo)

# Convert tensor to image for visualization
def tensor_to_image(tensor):
    tensor = tensor.cpu().squeeze(0)  # Move to CPU & remove batch dim
    tensor = tensor.permute(1, 2, 0)  # Change shape to (H, W, C)
    image = tensor * 0.5 + 0.5  # Rescale to [0, 1]
    return image.numpy()

# Plot results
plt.figure(figsize=(10, 5))

# Original photo
plt.subplot(121)
plt.title('Original Photo')
plt.imshow(tensor_to_image(example_photo))

# Generated Monet-style image
plt.subplot(122)
plt.title('Generated Monet')
plt.imshow(tensor_to_image(generated_monet))

plt.show()

"""# Discriminator Model"""

class Discriminator(nn.Module):
    def __init__(self):
        super(Discriminator, self).__init__()

        # Creates layers to downsample the image
        self.down1 = self.downsample(3, 64, 4, normalize=False)
        self.down2 = self.downsample(64, 128, 4)
        self.down3 = self.downsample(128, 256, 4)

        # Zero padding to prepare for convolutional layer
        self.zero_pad1 = nn.ZeroPad2d(1)  # (bs, 34, 34, 256)
        # Processes the feature map with convolutional layer
        self.conv = nn.Conv2d(256, 512, kernel_size=4, stride=1, padding=0, bias=False)  # (bs, 31, 31, 512)
        self.norm1 = nn.InstanceNorm2d(512)


        self.leaky_relu = nn.LeakyReLU(0.2)

        # Final zero padding and convolutional layer
        self.zero_pad2 = nn.ZeroPad2d(1)  # (bs, 33, 33, 512)
        self.last = nn.Conv2d(512, 1, kernel_size=4, stride=1, padding=0)  # (bs, 30, 30, 1)

    def downsample(self, in_channels, out_channels, kernel_size, normalize=True):
        """Helper function to create a downsample block."""
        layers = []
        layers.append(nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size, stride=2, padding=1, bias=False))
        if normalize:
            layers.append(nn.InstanceNorm2d(out_channels))
        layers.append(nn.LeakyReLU(0.2))
        return nn.Sequential(*layers)
    #Forward method applys all the layers
    def forward(self, x):
        # Apply downsample blocks
        x = self.down1(x)
        x = self.down2(x)
        x = self.down3(x)

        # Apply zero padding and convolutional layers
        x = self.zero_pad1(x)
        x = self.conv(x)
        x = self.norm1(x)
        x = self.leaky_relu(x)

        # Apply final zero padding and convolutional layer
        x = self.zero_pad2(x)
        x = self.last(x)
        return x

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
discriminator = Discriminator().to(device)


example_photo = example_photo.to(device)
output = discriminator(example_photo)
print("Discriminator output shape:", output.shape)

def process_single_image(img_tensor, discriminator):
    """
    Process a single image tensor through the discriminator.

    Args:
        img_tensor: A tensor representing the image (already transformed)
        discriminator: The discriminator model

    Returns:
        The discriminator's output
    """
    # Make sure img_tensor is on the correct device
    img_tensor = img_tensor.to(next(discriminator.parameters()).device)

    # Get the discriminator's output
    with torch.no_grad():  # No need to track gradients for inference
        output = discriminator(img_tensor)

    return output

# Example usage:
output = process_single_image(example_monet, discriminator)
print(f"Discriminator output shape: {output.shape}")

"""### Test discriminator with single generated Monet-image from above:"""

output = process_single_image(generated_monet, discriminator)
print(f"Discriminator output shape: {output.shape}")

print(output)