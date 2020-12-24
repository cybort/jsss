from typing import Callable, List, Optional, Union

import pytorch_lightning as pl
from torch.tensor import Tensor
from torch.utils.data import random_split, DataLoader

from ...dataset.spectrogram import JSSS_spec
from ....corpus import Subtype


class JSSS_spec_DataModule(pl.LightningDataModule):
    """
    JSSS_spec dataset's PyTorch Lightning datamodule
    """

    def __init__(
        self,
        batch_size: int,
        download: bool,
        subtypes: List[Subtype] = ["short-form/basic5000"],
        transform: Callable[[Tensor], Tensor] = lambda i: i,
        corpus_adress: Optional[str] = None,
        dataset_adress: Optional[str] = None,
        resample_sr: Optional[int] = None,
    ):
        super().__init__()
        self.n_batch = batch_size
        self.download = download
        self._subtypes = subtypes
        self.transform = transform
        self.corpus_adress = corpus_adress
        self.dataset_adress = dataset_adress
        self._resample_sr = resample_sr

    def prepare_data(self, *args, **kwargs) -> None:
        pass

    def setup(self, stage: Union[str, None] = None) -> None:
        if stage == "fit" or stage is None:
            dataset_train = JSSS_spec(self._subtypes, self.download, None, None, self._resample_sr, self.transform)
            n_train = len(dataset_train)
            self.data_train, self.data_val = random_split(dataset_train, [n_train - 10, 10])
        if stage == "test" or stage is None:
            self.data_test = JSSS_spec(self._subtypes, self.download, None, None, self._resample_sr, self.transform)

    def train_dataloader(self, *args, **kwargs):
        return DataLoader(self.data_train, batch_size=self.n_batch)

    def val_dataloader(self, *args, **kwargs):
        return DataLoader(self.data_val, batch_size=self.n_batch)

    def test_dataloader(self, *args, **kwargs):
        return DataLoader(self.data_test, batch_size=self.n_batch)


if __name__ == "__main__":
    print("This is datamodule/waveform.py")
    # If you use batch (n>1), transform function for Tensor shape rearrangement is needed
    dm_JSSS_spec = JSSS_spec_DataModule(1, download=True)

    # download & preprocessing
    dm_JSSS_spec.prepare_data()

    # runtime setup
    dm_JSSS_spec.setup(stage="fit")

    # yield dataloader
    dl = dm_JSSS_spec.train_dataloader()
    print(next(iter(dl)))
    print("datamodule/waveform.py test passed")