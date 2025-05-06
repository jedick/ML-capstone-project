"""
Kickoff training on target datasets.

NOTE: Training right now doesn't work with multiple GPU's and DDP. This is known issue;
see for instance https://lightning.ai/forums/t/gradient-checkpointing-ddp-nan/398/7.
"""


import argparse
import subprocess


def get_args():
    help_gpus = """GPU's used for training.
    If a single int, specifies the number of GPU's.
    If a comma-separated list, specifies the specific device ID's.
    For a single specific device, write it as `[device-num],`
    """

    parser = argparse.ArgumentParser("Kick off model training.")
    parser.add_argument(
        "--dataset",
        type=str,
        help="The dataset to train on.",
        choices=["citint", "scifact_20", "scifact_10", "scifact", "healthver", "covidfact"],
    )
    parser.add_argument("--gpus", type=str, help=help_gpus, default="1")
    parser.add_argument("--debug", action="store_true")

    parser.add_argument(
        "--gradient_checkpointing",
        action="store_true",
        help="Turning this on decreases memory usage at the cost of slower training",
    )

    # Added by jmd 20241218
    parser.add_argument("--epochs", type=int, help="Number of epochs", default=5)
    parser.add_argument("--ckpt", type=str, help="Starting checkpoint file", default="checkpoints/fever_sci.ckpt")
    # Added by jmd 20241222
    parser.add_argument("--rationale_weight", type=str, help="Rationale weight", default="15.0")

    args = parser.parse_args()
    return args


def main():
    args = get_args()
    gpus = args.gpus

    # Deal with case of specific devides
    if "," in gpus:
        n_gpus = len([x for x in gpus.split(",") if x])
    else:
        n_gpus = int(gpus)

    if n_gpus not in [1, 2, 4, 8]:
        raise ValueError("The number of GPU's must be a power of 2.")

    #epochs = 5
    workers_per_gpu = 4  # Number of CPU's per gpu.
    effective_batch_size = 8  # Desired effective batch size.
    accumulate_grad_batches = effective_batch_size // n_gpus
    num_workers = workers_per_gpu * n_gpus

    cmd = [
        "python",
        "multivers/train.py",
        "--result_dir",
        "checkpoints_user",
        "--datasets",
        args.dataset,
        "--starting_checkpoint",
        args.ckpt,
        "--experiment_name",
        args.dataset,
        "--num_workers",
        num_workers,
        "--gpus",
        gpus,
        "--accumulate_grad_batches",
        accumulate_grad_batches,
        "--lr",
        "1e-5",
        "--precision",
        16,
        "--max_epochs",
        args.epochs,
        "--scheduler_total_epochs",
        args.epochs,
        "--train_batch_size",
        1,
        "--eval_batch_size",
        2,
        "--rationale_weight",
        args.rationale_weight,
        "--encoder_name",
        "longformer-large-science",
        "--no_reweight_labels",
    ]

    if args.debug == True:
        cmd.append("--debug")

    # If training on more than 1 gpu, use DDP accelerator.
    if n_gpus > 1:
        cmd.extend(["--accelerator", "ddp"])

    # Turn on gradient checkpointing if requested.
    if args.gradient_checkpointing:
        cmd.append("--gradient_checkpointing")

    subprocess.call(map(str, cmd))


if __name__ == "__main__":
    main()
