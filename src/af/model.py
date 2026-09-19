import torch
import torch.nn as nn
import segmentation_models_pytorch as smp

def build_af_model(in_channels: int):
    return smp.Unet(
        encoder_name="efficientnet-b0",
        encoder_weights="imagenet",
        in_channels=in_channels,
        classes=1,
        activation=None,
    )