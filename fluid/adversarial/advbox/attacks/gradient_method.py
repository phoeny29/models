"""
This module provide the attack method for Iterator FGSM's implement.
"""
from __future__ import division

import logging
from collections import Iterable

import numpy as np

from .base import Attack

__all__ = [
    'GradientMethodAttack', 'FastGradientSignMethodAttack', 'FGSM',
    'FastGradientSignMethodTargetedAttack', 'FGSMT',
    'BasicIterativeMethodAttack', 'BIM',
    'IterativeLeastLikelyClassMethodAttack', 'ILCM'
]


class GradientMethodAttack(Attack):
    """
    This class implements gradient attack method, and is the base of FGSM, BIM,
    ILCM, etc.
    """

    def __init__(self, model, support_targeted=True):
        """
        :param model(model): The model to be attacked.
        :param support_targeted(bool): Does this attack method support targeted.
        """
        super(GradientMethodAttack, self).__init__(model)
        self.support_targeted = support_targeted

    def _apply(self,
               adversary,
               norm_ord=np.inf,
               epsilons=0.01,
               steps=1,
               epsilon_steps=100):
        """
        Apply the gradient attack method.
        :param adversary(Adversary):
            The Adversary object.
        :param norm_ord(int):
            Order of the norm, such as np.inf, 1, 2, etc. It can't be 0.
        :param epsilons(list|tuple|int):
            Attack step size (input variation).
            Largest step size if epsilons is not iterable.
        :param steps:
            The number of attack iteration.
        :param epsilon_steps:
            The number of Epsilons' iteration for each attack iteration.
        :return:
            adversary(Adversary): The Adversary object.
        """
        if norm_ord == 0:
            raise ValueError("L0 norm is not supported!")

        if not self.support_targeted:
            if adversary.is_targeted_attack:
                raise ValueError(
                    "This attack method doesn't support targeted attack!")

        if not isinstance(epsilons, Iterable):
            epsilons = np.linspace(0, epsilons, num=epsilon_steps)

        pre_label = adversary.original_label
        min_, max_ = self.model.bounds()

        assert self.model.channel_axis() == adversary.original.ndim
        assert (self.model.channel_axis() == 1 or
                self.model.channel_axis() == adversary.original.shape[0] or
                self.model.channel_axis() == adversary.original.shape[-1])

        for epsilon in epsilons[:]:
            step = 1
            adv_img = adversary.original
            for i in range(steps):
                if epsilon == 0.0:
                    continue
                if adversary.is_targeted_attack:
                    gradient = -self.model.gradient(adv_img,
                                                    adversary.target_label)
                else:
                    gradient = self.model.gradient(adv_img,
                                                   adversary.original_label)
                if norm_ord == np.inf:
                    gradient_norm = np.sign(gradient)
                else:
                    gradient_norm = gradient / self._norm(
                        gradient, ord=norm_ord)

                adv_img = adv_img + epsilon * gradient_norm * (max_ - min_)
                adv_img = np.clip(adv_img, min_, max_)
                adv_label = np.argmax(self.model.predict(adv_img))
                logging.info('step={}, epsilon = {:.5f}, pre_label = {}, '
                             'adv_label={}'.format(step, epsilon, pre_label,
                                                   adv_label))
                if adversary.try_accept_the_example(adv_img, adv_label):
                    return adversary
                step += 1
        return adversary

    @staticmethod
    def _norm(a, ord):
        if a.ndim == 1:
            return np.linalg.norm(a, ord=ord)
        if a.ndim == a.shape[0]:
            norm_shape = (a.ndim, reduce(np.dot, a.shape[1:]))
            norm_axis = 1
        else:
            norm_shape = (reduce(np.dot, a.shape[:-1]), a.ndim)
            norm_axis = 0
        return np.linalg.norm(a.reshape(norm_shape), ord=ord, axis=norm_axis)


class FastGradientSignMethodTargetedAttack(GradientMethodAttack):
    """
    "Fast Gradient Sign Method" is extended to support targeted attack.
    "Fast Gradient Sign Method" was originally implemented by Goodfellow et
    al. (2015) with the infinity norm.

    Paper link: https://arxiv.org/abs/1412.6572
    """

    def _apply(self, adversary, epsilons=0.01):
        return GradientMethodAttack._apply(
            self,
            adversary=adversary,
            norm_ord=np.inf,
            epsilons=epsilons,
            steps=1)


class FastGradientSignMethodAttack(FastGradientSignMethodTargetedAttack):
    """
    This attack was originally implemented by Goodfellow et al. (2015) with the
    infinity norm, and is known as the "Fast Gradient Sign Method".

    Paper link: https://arxiv.org/abs/1412.6572
    """

    def __init__(self, model):
        super(FastGradientSignMethodAttack, self).__init__(model, False)


class IterativeLeastLikelyClassMethodAttack(GradientMethodAttack):
    """
    "Iterative Least-likely Class Method (ILCM)" extends "BIM" to support
    targeted attack.
    "The Basic Iterative Method (BIM)" is to extend "FSGM". "BIM" iteratively
    take multiple small steps while adjusting the direction after each step.

    Paper link: https://arxiv.org/abs/1607.02533
    """

    def _apply(self, adversary, epsilons=0.01, steps=1000):
        return GradientMethodAttack._apply(
            self,
            adversary=adversary,
            norm_ord=np.inf,
            epsilons=epsilons,
            steps=steps)


class BasicIterativeMethodAttack(IterativeLeastLikelyClassMethodAttack):
    """
    FGSM is a one-step method. "The Basic Iterative Method (BIM)" iteratively
    take multiple small steps while adjusting the direction after each step.
    Paper link: https://arxiv.org/abs/1607.02533
    """

    def __init__(self, model):
        super(BasicIterativeMethodAttack, self).__init__(model, False)


FGSM = FastGradientSignMethodAttack
FGSMT = FastGradientSignMethodTargetedAttack
BIM = BasicIterativeMethodAttack
ILCM = IterativeLeastLikelyClassMethodAttack
