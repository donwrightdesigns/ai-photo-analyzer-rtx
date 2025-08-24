# simple alternative to the "internal" test_harness()

use strict;

unshift @INC, './lib';

use Test::Harness;

my @files = glob('t/*.t');

$Test::Harness::verbose = 0; # set to 1 for more verbosity

Test::Harness::runtests(sort { lc $a cmp lc $b } @files);
