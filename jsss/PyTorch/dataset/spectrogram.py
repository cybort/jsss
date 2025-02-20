from typing import Callable, List, NamedTuple, Optional, Union
from pathlib import Path

from torch import Tensor, save, load
from torch.utils.data.dataset import Dataset
# currently there is no stub in torchaudio [issue](https://github.com/pytorch/audio/issues/615)
from torchaudio import load as load_wav
from torchaudio.transforms import Spectrogram, Resample # type: ignore
from speechcorpusy.components.archive import hash_args, try_to_acquire_archive_contents, save_archive

from .waveform import get_dataset_wave_path, preprocess_as_wave
from ...corpus import ItemIdJSSS, Subtype, JSSS


def get_dataset_spec_path(dir_dataset: Path, id: ItemIdJSSS) -> Path:
    return dir_dataset / id.subtype / "specs" / f"{id.serial_num}.spec.pt"


def preprocess_as_spec(path_wav: Path, id: ItemIdJSSS, dir_dataset: Path, new_sr: Optional[int] = None) -> None:
    """Transform JSSS corpus contents into spectrogram Tensor.

    Before this preprocessing, corpus contents should be deployed.
    """
    
    waveform, _sr_orig = load_wav(path_wav)
    if new_sr is not None:
        waveform = Resample(_sr_orig, new_sr)(waveform)
    # :: [1, Length] -> [Length,]
    waveform: Tensor = waveform[0, :]
    # defaults: hop_length = win_length // 2, window_fn = torch.hann_window, power = 2
    spec: Tensor = Spectrogram(254)(waveform)
    path_spec = get_dataset_spec_path(dir_dataset, id)
    path_spec.parent.mkdir(parents=True, exist_ok=True)
    save(spec, path_spec)


class Datum_JSSS_spec_train(NamedTuple):
    spectrogram: Tensor
    label: str


class Datum_JSSS_spec_test(NamedTuple):
    waveform: Tensor
    spectrogram: Tensor
    label: str


class JSSS_spec(Dataset): # I failed to understand this error
    """Audio spectrogram dataset from JSSS speech corpus.
    """
    def __init__(
        self,
        train: bool,
        resample_sr: Optional[int],
        subtypes: List[Subtype] = ["short-form/basic5000"],
        download_corpus: bool = False,
        corpus_adress: Optional[str] = None,
        dataset_dir_adress: Optional[str] = None,
        transform: Callable[[Tensor], Tensor] = (lambda i: i),
    ):
        """
        Args:
            train: train_dataset if True else validation/test_dataset.
            resample_sr: If not None, resample with specified sampling rate.
            subtypes: Sub corpus types.
            download_corpus: Whether download the corpus or not when dataset is not found.
            corpus_adress: URL/localPath of corpus archive (remote url, like `s3::`, can be used). None use default URL.
            dataset_dir_adress: URL/localPath of JSSS_spec dataset directory (remote url, like `s3::`, can be used).
            transform: Tensor transform on load.
        """

        # Design Notes:
        #   Sampling rate:
        #     Sampling rates of dataset A and B should match, so `sampling_rate` is not a optional, but required argument.
        #   Download:
        #     Dataset is often saved in the private adress, so there is no `download_dataset` safety flag.
        #     `download` is common option in torchAudio datasets.
        #   Dataset archive name:
        #     Dataset contents differ based on argument, so archive should differ when arguments differ.
        #     It is guaranteed by name by argument hash.

        # Store parameters.
        self._train = train
        self._resample_sr = resample_sr
        self._transform = transform

        self._corpus = JSSS(corpus_adress, download_corpus)
        arg_hash = hash_args(subtypes, resample_sr)
        JSSS_spec_root = Path(".")/"tmp"/"JSSS_spec"
        self._path_contents_local = JSSS_spec_root/"contents"/arg_hash
        dataset_dir_adress = dataset_dir_adress if dataset_dir_adress else str(JSSS_spec_root/"archive")
        dataset_archive_adress = f"{dataset_dir_adress}/{arg_hash}.zip"

        # Prepare data identities.
        self._ids: List[ItemIdJSSS] = list(filter(lambda id: id.subtype in subtypes, self._corpus.get_identities()))

        # Deploy dataset contents.
        contents_acquired = try_to_acquire_archive_contents(dataset_archive_adress, self._path_contents_local)
        if not contents_acquired:
            # Generate the dataset contents from corpus
            print("Dataset archive file is not found. Automatically generating new dataset...")
            self._generate_dataset_contents()
            save_archive(self._path_contents_local, dataset_archive_adress)
            print("Dataset contents was generated and archive was saved.")

    def _generate_dataset_contents(self) -> None:
        """Generate dataset with corpus auto-download and preprocessing.
        """

        self._corpus.get_contents()
        print("Preprocessing...")
        for id in self._ids:
            path_wav = self._corpus.get_item_path(id)
            preprocess_as_spec(path_wav, id, self._path_contents_local, self._resample_sr)
            preprocess_as_wave(path_wav, id, self._path_contents_local, self._resample_sr)
        print("Preprocessed.")

    def _load_datum(self, id: ItemIdJSSS) -> Union[Datum_JSSS_spec_train, Datum_JSSS_spec_test]:
        spec_path = get_dataset_spec_path(self._path_contents_local, id)
        spec: Tensor = self._transform(load(spec_path))
        # todo: trains/evals
        if self._train:
            return Datum_JSSS_spec_train(spec, f"{id.subtype}-{id.serial_num}")
        else:
            waveform: Tensor = load(get_dataset_wave_path(self._path_contents_local, id))
            return Datum_JSSS_spec_test(waveform, spec, f"{id.subtype}-{id.serial_num}")

    def __getitem__(self, n: int) -> Union[Datum_JSSS_spec_train, Datum_JSSS_spec_test]:
        """Load the n-th sample from the dataset.
        Args:
            n : The index of the datum to be loaded
        """
        return self._load_datum(self._ids[n])

    def __len__(self) -> int:
        return len(self._ids)


if __name__ == "__main__":
    # Dataset load demo
    from jsss.PyTorch.dataset.spectrogram import JSSS_spec


    ds = JSSS_spec(True, ["short-form/basic5000"], download_corpus=True)
    ds = JSSS_spec(True, ["short-form/onomatopee300"], download_corpus=True)
    ds = JSSS_spec(True, ["short-form/voiceactress100"], download_corpus=True)
    ds = JSSS_spec(True, ["long-form/katsura-masakazu"], download_corpus=True)
    ds = JSSS_spec(True, ["long-form/udon"], download_corpus=True)
    ds = JSSS_spec(True, ["long-form/washington-dc"], download_corpus=True)
    ds = JSSS_spec(True, ["simplification"], download_corpus=True)