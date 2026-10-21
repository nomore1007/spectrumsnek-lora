# Third-party notices

## LoraReceiverStandalone

- Project: https://github.com/mmmaly/LoraReceiverStandalone
- Author/upstream maintainer: mmmaly
- Pinned revision used by setup: beb7bad8554dc78133c90e83d594c2b49d00d1ea
- Local changes: none; setup checks out the upstream repository and builds its lora_rx target.

The upstream README describes this as a standalone C/C++ reimplementation based on DSP algorithms from [gr-lora_sdr](https://github.com/tapparelj/gr-lora_sdr). The pinned repository tree does not contain a conventional root LICENSE file. Its source comments identify the gr-lora_sdr lineage, and included KissFFT source carries BSD-3-Clause notices.

This is a hobbyist integration, but the exact license applicable to the standalone receiver and the relationship to its GPL-3.0 DSP lineage have not been conclusively established from the upstream repository metadata. Preserve upstream source files and notices when building; do not represent the upstream decoder as MIT-licensed. Revisit this note before redistributing binaries or packaging the decoder into a broader distribution.

## KissFFT

The upstream receiver includes KissFFT source attributed to Mark Borgerding, with BSD-3-Clause notices in the source. See https://github.com/mborgerding/kissfft for the upstream project and license text.

## SpectrumSnek wrapper

The SpectrumSnek plugin wrapper, tests, setup script, and documentation in this repository are covered by LICENSE.txt, except for the separately checked-out upstream decoder and its dependencies.
