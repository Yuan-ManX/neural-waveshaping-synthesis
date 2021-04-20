import os

import gin
import numpy as np
import pytorch_lightning as pl
import torch


class URMPDataset(torch.utils.data.Dataset):
    def __init__(self, path: str, split: str = "train", load_to_memory: bool = True):
        super().__init__()
        # split = "train"
        self.load_to_memory = load_to_memory

        self.split_path = os.path.join(path, split)
        self.data_list = [
            f.replace("audio_", "")
            for f in os.listdir(os.path.join(self.split_path, "audio"))
            if f[-4:] == ".npy"
        ]
        if load_to_memory:
            self.audio = [
                np.load(os.path.join(self.split_path, "audio", "audio_%s" % name))
                for name in self.data_list
            ]
            self.control = [
                np.load(os.path.join(self.split_path, "control", "control_%s" % name))
                for name in self.data_list
            ]

        self.data_mean = np.load(os.path.join(path, "data_mean.npy"))
        self.data_std = np.load(os.path.join(path, "data_std.npy"))

    def __len__(self):
        return len(self.data_list)

    def __getitem__(self, idx):
        # idx = 10
        if self.load_to_memory:
            audio = self.audio[idx]
            control = self.control[idx]
        else:
            name = self.data_list[idx]
            audio_name = "audio_%s" % name
            control_name = "control_%s" % name

            audio = np.load(os.path.join(self.split_path, "audio", audio_name))
            control = np.load(os.path.join(self.split_path, "control", control_name))
        denormalised_control = (control * self.data_std) + self.data_mean

        return {
            "audio": audio,
            "f0": denormalised_control[0:1, :],
            "amp": denormalised_control[1:2, :],
            "control": control,
        }


@gin.configurable
class URMPDataModule(pl.LightningDataModule):
    def __init__(
        self,
        urmp_root: str,
        instrument: str,
        batch_size: int = 16,
        load_to_memory: bool = True,
        **dataloader_args
    ):
        super().__init__()
        self.data_dir = os.path.join(urmp_root, instrument)
        self.batch_size = batch_size
        self.dataloader_args = dataloader_args
        self.load_to_memory = load_to_memory

    def prepare_data(self):
        pass

    def setup(self, stage: str = None):
        if stage == "fit":
            self.urmp_train = URMPDataset(self.data_dir, "train", self.load_to_memory)
            self.urmp_val = URMPDataset(self.data_dir, "val", self.load_to_memory)
        elif stage == "test" or stage is None:
            self.urmp_test = URMPDataset(self.data_dir, "test", self.load_to_memory)

    def _make_dataloader(self, dataset):
        return torch.utils.data.DataLoader(
            dataset, self.batch_size, **self.dataloader_args
        )

    def train_dataloader(self):
        return self._make_dataloader(self.urmp_train)

    def val_dataloader(self):
        return self._make_dataloader(self.urmp_val)

    def test_dataloader(self):
        return self._make_dataloader(self.urmp_test)