import click
import gin
import pytorch_lightning as pl

from nts.data.urmp import URMPDataModule
from nts.models.timbre_transfer import TimbreTransfer
from nts.models.timbre_transfer_newt import TimbreTransferNEWT


@gin.configurable
def get_model(model, restore_checkpoint):
    if restore_checkpoint == "":
        return model()
    else:
        return model.load_from_checkpoint(restore_checkpoint)


@gin.configurable
def early_stopping(patience):
    return pl.callbacks.early_stopping.EarlyStopping(
        monitor="val/loss", patience=patience
    )


@gin.configurable
def gradient_clipping(norm):
    return norm


@click.command()
@click.option("--gin-file", prompt="Gin config file")
@click.option("--device", default="cuda")
@click.option("--instrument", default="vn")
@click.option("--load-data-to-memory/--load-data-from-disk", default=True)
@click.option("--with-wandb/--without-wandb", default=True)
@click.option("--restore-checkpoint", default="")
def main(
    gin_file, device, instrument, load_data_to_memory, with_wandb, restore_checkpoint
):
    gin.parse_config_file(gin_file)
    model = get_model(restore_checkpoint=restore_checkpoint)
    data = URMPDataModule(
        "/import/c4dm-datasets/URMP/synth-dataset/4s-dataset",
        instrument,
        load_to_memory=load_data_to_memory,
        num_workers=16,
        shuffle=True,
    )

    lr_logger = pl.callbacks.LearningRateMonitor(logging_interval="epoch")
    logger = pl.loggers.WandbLogger(project="neural-timbre-shaping", log_model=True)
    logger.watch(model, log="parameters")

    checkpointing = pl.callbacks.ModelCheckpoint(monitor="val/loss", save_top_k=5)
    early_stopping_callback = early_stopping()
    grad_norm = gradient_clipping()

    trainer = pl.Trainer(
        logger=logger,
        callbacks=[lr_logger, early_stopping_callback, checkpointing],
        gpus=device,
        # val_check_interval=100,
        # check_val_every_n_epoch=5,
        max_epochs=5000,
        # overfit_batches=1,
        gradient_clip_val=grad_norm,
        # limit_val_batches=0.01
    )

    trainer.fit(model, data)


if __name__ == "__main__":
    main()