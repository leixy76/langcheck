from __future__ import annotations

import random

import jaconv


def to_full_width(
    instances: list[str] | str,
    *,
    aug_char_p: float = 1.0,
    num_perturbations: int = 1,
) -> list[str]:
    """Applies a text perturbation to each string in instances (usually a list
    of prompts) where some ascii characters are converted into full-width
    characters defined in UTF-8.

    Args:
        instances: A single string or a list of strings to be augmented.
        aug_char_p: Percentage of all characters that will be augmented.
        num_perturbations: The number of perturbed instances to generate for
            each string in instances.

    Returns:
        A list of perturbed instances.
    """

    instances = [instances] if isinstance(instances, str) else instances
    perturbed_instances = []
    for instance in instances:
        for _ in range(num_perturbations):
            perturbed_instance = ""
            for char in instance:
                if random.random() > aug_char_p:
                    perturbed_instance += char  # No augmentation
                else:
                    perturbed_instance += jaconv.h2z(
                        char, kana=False, ascii=True, digit=True
                    )
            perturbed_instances.append(perturbed_instance)

    return perturbed_instances
