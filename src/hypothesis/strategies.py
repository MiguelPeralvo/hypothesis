# coding=utf-8

# Copyright (C) 2013-2015 David R. MacIver (david@drmaciver.com)

# This file is part of Hypothesis (https://github.com/DRMacIver/hypothesis)

# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at http://mozilla.org/MPL/2.0/.

# END HEADER

from __future__ import division, print_function, absolute_import, \
    unicode_literals

import math
from random import Random
from decimal import Decimal
from fractions import Fraction

import hypothesis.specifiers as spec
from hypothesis.errors import InvalidArgument
from hypothesis.control import assume
from hypothesis.settings import Settings
from hypothesis.searchstrategy import SearchStrategy, strategy
from hypothesis.internal.compat import text_type, binary_type, \
    integer_types

__all__ = [
    'just', 'one_of',

    'booleans', 'integers', 'floats', 'complex_numbers', 'fractions',
    'decimals',

    'text', 'binary',

    'tuples', 'lists', 'sets', 'frozensets',
    'dictionaries', 'fixed_dictionaries',

    'builds',

    'streaming', 'basic',
]


def just(value):
    """Return a strategy which only generates value.

    Note: value is not copied. Be wary of using mutable values.

    """
    from hypothesis.searchstrategy.misc import JustStrategy
    return JustStrategy(value)


def none():
    """Return a strategy which only generates None."""
    return just(None)


def one_of(arg, *args):
    """Return a strategy which generates values from any of the argument
    strategies."""

    if not args:
        check_strategy(arg)
        return arg
    from hypothesis.searchstrategy.strategies import OneOfStrategy
    args = (arg,) + args
    for arg in args:
        check_strategy(arg)
    return OneOfStrategy(args)


def integers(min_value=None, max_value=None):
    """Returns a strategy which generates integers (in Python 2 these may be
    ints or longs).

    If min_value is not None then all values will be >=
    min_value. If max_value is not None then all values will be <= max_value

    """

    from hypothesis.searchstrategy.numbers import IntegersFromStrategy, \
        BoundedIntStrategy, RandomGeometricIntStrategy, WideRangeIntStrategy

    if min_value is None:
        if max_value is None:
            return (
                RandomGeometricIntStrategy() |
                WideRangeIntStrategy()
            )
        else:
            check_type(integer_types, max_value)
            return IntegersFromStrategy(0).map(lambda x: max_value - x)
    else:
        check_type(integer_types, min_value)
        if max_value is None:
            return IntegersFromStrategy(min_value)
        else:
            if min_value == max_value:
                return just(min_value)
            elif min_value > max_value:
                raise InvalidArgument(
                    'Cannot have max_value=%r < min_value=%r' % (
                        max_value, min_value
                    ))
            return BoundedIntStrategy(min_value, max_value)


def booleans():
    """Returns a strategy which generates instances of bool."""
    from hypothesis.searchstrategy.misc import BoolStrategy
    return BoolStrategy()


def floats(min_value=None, max_value=None):
    """Returns a strategy which generates floats. If min_value is not None,
    all values will be >= min_value. If max_value is not None, all values will
    be <= max_value.

    Where not explicitly ruled out by the bounds, all of infinity, -infinity
    and NaN are possible values generated by this strategy.
    """

    for e in (min_value, max_value):
        if e is not None and math.isnan(e):
            raise InvalidArgument('nan is not a valid end point')

    if min_value == float('-inf'):
        min_value = None
    if max_value == float('inf'):
        max_value = None

    from hypothesis.searchstrategy.numbers import WrapperFloatStrategy, \
        GaussianFloatStrategy, BoundedFloatStrategy, ExponentialFloatStrategy,\
        JustIntFloats, NastyFloats, FullRangeFloats, \
        FixedBoundedFloatStrategy, FloatsFromBase
    if min_value is None and max_value is None:
        return WrapperFloatStrategy(
            GaussianFloatStrategy() |
            BoundedFloatStrategy() |
            ExponentialFloatStrategy() |
            JustIntFloats() |
            NastyFloats() |
            FullRangeFloats()
        )
    elif min_value is not None and max_value is not None:
        if max_value < min_value:
            raise InvalidArgument(
                'Cannot have max_value=%r < min_value=%r' % (
                    max_value, min_value
                ))
        elif min_value == max_value:
            return just(min_value)
        elif math.isinf(max_value - min_value):
            assert min_value < 0 and max_value > 0
            return floats(min_value=0, max_value=max_value) | floats(
                min_value=min_value, max_value=0
            )
        return FixedBoundedFloatStrategy(min_value, max_value)
    elif min_value is not None:
        return FloatsFromBase(
            base=min_value, sign=1,
        ) | just(float('inf'))
    else:
        assert max_value is not None
        return FloatsFromBase(
            base=max_value, sign=-1
        ) | just(float('-inf'))


def complex_numbers():
    """Returns a strategy that generates complex numbers."""
    from hypothesis.searchstrategy.numbers import ComplexStrategy
    return ComplexStrategy(
        tuples(floats(), floats())
    )


def tuples(*args):
    """Return a strategy which generates a tuple of the same length as args by
    generating the value at index i from args[i].

    e.g. tuples(integers(), integers()) would generate a tuple of length
    two with both values an integer.

    """
    for arg in args:
        check_strategy(arg)
    from hypothesis.searchstrategy.collections import TupleStrategy
    return TupleStrategy(args, tuple)


def sampled_from(elements):
    """Returns a strategy which generates any value present in the iterable
    elements.

    Note that as with just, values will not be copied and thus you
    should be careful of using mutable data

    """

    from hypothesis.searchstrategy.misc import SampledFromStrategy
    elements = tuple(iter(elements))
    if not elements:
        raise InvalidArgument(
            'sampled_from requires at least one value'
        )
    if len(elements) == 1:
        return just(elements[0])
    return SampledFromStrategy(elements)


def lists(elements=None, min_size=None, average_size=None, max_size=None):
    """Returns a list containining values drawn from elements length in the
    interval [min_size, max_size] (no bounds in that direction if these are
    None). If max_size is 0 then elements may be None and only the empty list
    will be drawn.

    average_size may be used as a size hint to roughly control the size
    of list but it may not be the actual average of sizes you get, due
    to a variety of factors.

    """

    check_valid_sizes(min_size, average_size, max_size)
    from hypothesis.searchstrategy.collections import ListStrategy, \
        SingleElementListStrategy
    if min_size is None:
        min_size = 0
    if average_size is None:
        if max_size is None:
            average_size = Settings.default.average_list_length
        else:
            average_size = (min_size + max_size) * 0.5

    if elements is None or (max_size is not None and max_size <= 0):
        if max_size is None or max_size > 0:
            raise InvalidArgument(
                'Cannot create non-empty lists without an element type'
            )
        else:
            return ListStrategy(())
    else:
        check_strategy(elements)
        if elements.template_upper_bound == 1:
            from hypothesis.searchstrategy.numbers import IntegersFromStrategy
            if max_size is None:
                length_strat = IntegersFromStrategy(
                    min_size, average_size=average_size - min_size)
            else:
                length_strat = integers(min_size, max_size)
            return SingleElementListStrategy(elements, length_strat)
        return ListStrategy(
            (elements,), average_length=average_size,
            min_size=min_size, max_size=max_size,
        )


def sets(elements=None, min_size=None, average_size=None, max_size=None):
    """This has the same behaviour as lists, but returns sets instead.

    Note that Hypothesis cannot tell if values are drawn from elements
    are hashable until running the test, so you can define a strategy
    for sets of an unhashable type but it will fail at test time.

    """
    check_valid_sizes(min_size, average_size, max_size)
    from hypothesis.searchstrategy.collections import SetStrategy
    if max_size == 0:
        return SetStrategy(())
    check_strategy(elements)
    if min_size is not None and elements.template_upper_bound < min_size:
        raise InvalidArgument((
            'Cannot generate sets of size %d from %r, which contains '
            'no more than %d distinct values') % (
                min_size, elements, elements.template_upper_bound,
        ))
    result = SetStrategy(
        (elements,),
        average_length=average_size or Settings.default.average_list_length,
        max_size=max_size,
    )
    if min_size is not None:
        result = result.filter(lambda x: len(x) >= min_size)
    return result


def frozensets(elements=None, min_size=None, average_size=None, max_size=None):
    """This is identical to the sets function but instead returns
    frozensets."""
    from hypothesis.searchstrategy.collections import FrozenSetStrategy
    return FrozenSetStrategy(sets(elements, min_size, average_size, max_size))


def fixed_dictionaries(mapping):
    """Generate a dictionary of the same type as mapping with a fixed set of
    keys mapping to strategies. mapping must be a dict subclass.

    Generated values have all keys present in mapping, with the
    corresponding values drawn from mapping[key]. If mapping is an
    instance of OrderedDict the keys will also be in the same order,
    otherwise the order is arbitrary.

    """
    from hypothesis.searchstrategy.collections import FixedKeysDictStrategy
    check_type(dict, mapping)
    for v in mapping.values():
        check_type(SearchStrategy, v)
    return FixedKeysDictStrategy(mapping)


def dictionaries(
    keys, values, dict_class=dict,
    min_size=None, average_size=None, max_size=None
):
    """Generates dictionaries of type dict_class with keys drawn from the keys
    argument and values drawn from the values argument.

    The size parameters have the same interpretation as for lists.

    """
    check_valid_sizes(min_size, average_size, max_size)
    if max_size == 0:
        return fixed_dictionaries(dict_class())
    check_strategy(keys)
    check_strategy(values)

    def build_dict(data):
        result = dict_class()
        for k, v in data:
            result[k] = v
            if max_size is not None and len(result) >= max_size:
                break
        assume(min_size is None or len(result) >= min_size)
        return result

    if min_size is not None:
        base_average = min_size * 2
        average_size = max(average_size or 0, base_average)

    return lists(
        tuples(keys, values),
        min_size=min_size, average_size=average_size,
    ).map(build_dict)


def streaming(elements):
    """Generates an infinite stream of values where each value is drawn from
    elements.

    The result is iterable (the iterator will never terminate) and
    indexable.

    """
    check_strategy(elements)
    from hypothesis.searchstrategy.streams import StreamStrategy
    return StreamStrategy(elements)


def text(
    alphabet=None,
    min_size=None, average_size=None, max_size=None
):
    """Generates values of a unicode text type (unicode on python 2, str on
    python 3) with values drawn from alphabet, which should be an iterable of
    length one strings or a strategy generating such. If it is None it will
    default to generating the full unicode range. If it is an empty collection
    this will only generate empty strings.

    min_size, max_size and average_size have the usual interpretations.

    """
    from hypothesis.searchstrategy.strings import OneCharStringStrategy, \
        StringStrategy
    if alphabet is None:
        char_strategy = OneCharStringStrategy()
    elif not alphabet:
        if (min_size or 0) > 0:
            raise InvalidArgument(
                'Invalid min_size %r > 0 for empty alphabet' % (
                    min_size,
                )
            )
        return just('')
    elif isinstance(alphabet, SearchStrategy):
        char_strategy = alphabet
    else:
        char_strategy = sampled_from(text_type(alphabet))
    return StringStrategy(lists(
        char_strategy, average_size=average_size, min_size=min_size,
        max_size=max_size
    ))


def binary(
    min_size=None, average_size=None, max_size=None
):
    """Generates the appropriate binary type (str in python 2, binary in python
    3).

    min_size, average_size and max_size have the usual interpretations.

    """
    from hypothesis.searchstrategy.strings import BinaryStringStrategy
    return BinaryStringStrategy(
        lists(
            integers(min_value=0, max_value=255),
            average_size=average_size, min_size=min_size, max_size=max_size
        )
    )


def basic(
    basic=None,
    generate_parameter=None, generate=None, simplify=None, copy=None
):
    """Provides a facility to write your own strategies with significantly less
    work.

    See documentation for more details.

    """
    from hypothesis.searchstrategy.basic import basic_strategy, BasicStrategy
    from copy import deepcopy
    if basic is not None:
        if isinstance(basic, type):
            basic = basic()
        check_type(BasicStrategy, basic)
        generate_parameter = generate_parameter or basic.generate_parameter
        generate = generate or basic.generate
        simplify = simplify or basic.simplify
        copy = copy or basic.copy
    return basic_strategy(
        parameter=generate_parameter,
        generate=generate, simplify=simplify, copy=copy or deepcopy
    )


def randoms():
    """Generates instances of Random (actually a Hypothesis specific
    RandomWithSeed class which displays what it was initially seeded with)"""
    from hypothesis.searchstrategy.misc import RandomStrategy
    return RandomStrategy(integers())


def fractions():
    """Generates instances of fractions.Fraction."""
    from fractions import Fraction
    return tuples(integers(), integers(min_value=1)).map(
        lambda t: Fraction(*t)
    )


def decimals():
    """Generates instances of decimals.Decimal."""
    from decimal import Decimal
    return (
        floats().map(Decimal) |
        fractions().map(
            lambda f: Decimal(f.numerator) / f.denominator
        )
    )


def builds(target, *args, **kwargs):
    """Generates values by drawing from args and kwargs and passing them to
    target in the appropriate argument position.

    e.g. builds(target,
    integers(), flag=booleans()) would draw an integer i and a boolean b and
    call target(i, flag=b).

    """
    def splat(value):
        return target(*value[0], **value[1])
    splat.__name__ = str(
        'splat(%s)' % (
            getattr(target, '__name__', type(target).__name__)
        )
    )
    return tuples(tuples(*args), fixed_dictionaries(kwargs)).map(splat)


# Private API below here

def check_type(typ, arg):
    if not isinstance(arg, typ):
        if isinstance(typ, type):
            typ_string = typ.__name__
        else:
            typ_string = 'one of %s' % (
                ', '.join(t.__name__ for t in typ))
        raise InvalidArgument(
            'Expected %s but got %r' % (typ_string, arg,))


def check_strategy(arg):
    check_type(SearchStrategy, arg)


def check_valid_size(value, name):
    if value is None:
        return
    check_type(integer_types + (float,), value)
    if value < 0:
        raise InvalidArgument('Invalid size %s %r < 0' % (value, name))
    if isinstance(value, float) and math.isnan(value):
        raise InvalidArgument('Invalid size %s %r' % (value, name))


def check_valid_sizes(min_size, average_size, max_size):
    check_valid_size(min_size, 'min_size')
    check_valid_size(max_size, 'max_size')
    check_valid_size(average_size, 'average_size')
    if max_size is not None:
        if min_size is not None:
            if max_size < min_size:
                raise InvalidArgument(
                    'Cannot have max_size=%r < min_size=%r' % (
                        max_size, min_size
                    ))

        if average_size is not None:
            if max_size < average_size:
                raise InvalidArgument(
                    'Cannot have max_size=%r < average_size=%r' % (
                        max_size, average_size
                    ))

    if average_size is not None and min_size is not None:
        if average_size < min_size:
            raise InvalidArgument(
                'Cannot have average_size=%r < min_size=%r' % (
                    average_size, min_size
                ))


@strategy.extend(tuple)
def define_tuple_strategy(specifier, settings):
    from hypothesis.searchstrategy.collections import TupleStrategy
    return TupleStrategy(
        tuple(strategy(d, settings) for d in specifier),
        tuple_type=type(specifier)
    )


@strategy.extend(dict)
def define_dict_strategy(specifier, settings):
    strategy_dict = {}
    for k, v in specifier.items():
        strategy_dict[k] = strategy(v, settings)
    return fixed_dictionaries(strategy_dict)


@strategy.extend(spec.Dictionary)
def define_dictionary_strategy(specifier, settings):
    return strategy(
        [(specifier.keys, specifier.values)], settings
    ).map(specifier.dict_class)


@strategy.extend(spec.IntegerRange)
def define_strategy_for_integer_Range(specifier, settings):
    return integers(min_value=specifier.start, max_value=specifier.end)


@strategy.extend(spec.FloatRange)
def define_strategy_for_float_Range(specifier, settings):
    return floats(specifier.start, specifier.end)


@strategy.extend_static(int)
def int_strategy(specifier, settings):
    return integers()


@strategy.extend(spec.IntegersFrom)
def integers_from_strategy(specifier, settings):
    return integers(min_value=specifier.lower_bound)


@strategy.extend_static(float)
def define_float_strategy(specifier, settings):
    return floats()


@strategy.extend_static(complex)
def define_complex_strategy(specifier, settings):
    return complex_numbers()


@strategy.extend_static(Decimal)
def define_decimal_strategy(specifier, settings):
    return decimals()


@strategy.extend_static(Fraction)
def define_fraction_strategy(specifier, settings):
    return fractions()


@strategy.extend(set)
def define_set_strategy(specifier, settings):
    if not specifier:
        return sets(max_size=0)
    else:
        with settings:
            return sets(one_of(*[strategy(s, settings) for s in specifier]))


@strategy.extend(frozenset)
def define_frozen_set_strategy(specifier, settings):
    if not specifier:
        return frozensets(max_size=0)
    else:
        with settings:
            return frozensets(
                one_of(*[strategy(s, settings) for s in specifier]))


@strategy.extend(list)
def define_list_strategy(specifier, settings):
    if not specifier:
        return lists(max_size=0)
    else:
        with settings:
            return lists(one_of(*[strategy(s, settings) for s in specifier]))


@strategy.extend_static(bool)
def bool_strategy(cls, settings):
    return booleans()


@strategy.extend(spec.Just)
def define_just_strategy(specifier, settings):
    return just(specifier.value)


@strategy.extend_static(Random)
def define_random_strategy(specifier, settings):
    return randoms()


@strategy.extend(spec.SampledFrom)
def define_sampled_strategy(specifier, settings):
    return sampled_from(specifier.elements)


@strategy.extend(type(None))
@strategy.extend_static(type(None))
def define_none_strategy(specifier, settings):
    return none()


@strategy.extend(spec.OneOf)
def strategy_for_one_of(oneof, settings):
    return one_of(*[strategy(d, settings) for d in oneof.elements])


@strategy.extend(spec.Strings)
def define_text_type_from_alphabet(specifier, settings):
    return text(alphabet=specifier.alphabet)


@strategy.extend_static(text_type)
def define_text_type_strategy(specifier, settings):
    return text()


@strategy.extend_static(binary_type)
def define_binary_strategy(specifier, settings):
    return binary()


@strategy.extend(spec.Streaming)
def stream_strategy(stream, settings):
    return streaming(strategy(stream.data, settings))
