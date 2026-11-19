# Verified speech model selection

## Intent
Allow users to compare English dictation accuracy and latency with the existing
base.en model and the larger small.en model. Medium is out of scope.

## Approach
Add CLI model selection, keeping base.en as the default for existing installs.
Install small.en through a separate setup script with a pinned checksum. A
selected missing or corrupted model fails closed. Changes apply after restarting
dictation. Keep speech local and retain the existing VAD and insertion safeguards.

The alternative of temporary, separate test configurations was not selected:
the user wants model selection as a supported feature.
