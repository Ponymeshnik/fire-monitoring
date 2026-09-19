import segmentation_models_pytorch as smp

def build_bs_model(in_channels: int):
    return smp.Unet(
        encoder_name="efficientnet-b3",
        encoder_weights="imagenet",
        in_channels=in_channels,
        classes=4,
        activation=None,
    )