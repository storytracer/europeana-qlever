# Compliance with the SPARQL 1.1 standard

Each commit to <https://github.com/ad-freiburg/qlever> triggers an automatic
conformance test against the W3C's SPARQL 1.1 test suite. The test results for
the current master branch can be found at <https://qlever.dev/sparql-conformance-ui> .

To find the test results for a specific commit, do the following:

1. Got to <https://github.com/ad-freiburg/qlever/commits/master/>
2. Click on the #... of the commit you are interested in
3. Search for "sparql-conformance"
4. Click on the link after "Details:"

You can also run the tests yourself, see <https://github.com/ad-freiburg/sparql-conformance>

## Intended deviations from the standard

When inspecting the test results, you will notice a number of "intended
deviations" (number shown in orange). To show only these deviations, open the
`Select test` dropdown, and in section `Status`, uncheck everything except
`Failed: Intended`. Click on anyone of the tests to see the details for that
test (index file, query file, expected result, actual result).

These deviations are almost entirely due to the fact that QLever currently does
not distinguish between the two types `xsd:int` and `xsd:integer`.
Specifically, QLever always uses `xsd:int` in results, even when the input
literal used `xsd:integer`. In the W3C test suite, all input literals with
integer values use `xsd:integer`.

Note that the only difference between `xsd:int` and `xsd:integer` is that
`xsd:int` is restricted to the range that can be represented by a signed 32-bit
integer, whereas `xsd:integer` can represent arbitrarily large integers. In the
W3C test suite, all integers fit into a signed 32-bit integer. QLever can
represent all integers that fit into a signed 60-bit integer, that is, integers
in the range from -576460752303423488 to 576460752303423487.

## Literals of type `geo:wktLiteral` that are `POINT`s

QLever represents `geo:wktLiteral`s that are `POINT`s as a 64-bit integer. This 
comes with a light loss of precision when the latitude or longitude is
specified with more than 6 decimal places. For example, the literals
`"POINT(1.1234567 2.1234567)"^^geo:wktLiteral` and
`"POINT(1.1234568 2.1234568)"^^geo:wktLiteral` become identical in QLever's
internal representation.

Besides the potential loss of precision, this can have another consequence.
Imagine a dataset that contains the following two triples:
```
:s1 geo:hasGeometry "POINT(1.1234567 2.1234567)"^^geo:wktLiteral .
:s2 geo:hasGeometry "POINT(1.1234568 2.1234568)"^^geo:wktLiteral .
```
In Qlever, both triples become identical after parsing. Since RDF dictates that
datasets are sets of triples, these two triples effectively become one triple
in QLever. Therefore, any query that matches both triples in the original dataset
will only match one triple in QLever.

## Subtle deviations regarding `OPTIONAL` and `EXISTS`

`OPTIONAL` and `EXISTS` each take a group graph pattern as argument (the
right-hand side, enclosed in `{ ... }`). This syntax suggests that the group
graph pattern enclosed in `{ ... }` is evaluated and then joined with the
enclosing group graph pattern (the left-hand side). This is what QLever
implements, but **unfortunately, this is not 100% what the SPARQL 1.1 standard
specifies**, much to the confusion of many users and experts alike.

The differences are subtle and very technical, and explained in the following.
For most queries, these differences do not matter. They only matter
when `FILTER`s are involved that use variables from both sides. Before you read
on, have a good night's sleep, drink some coffee, and sacrifice three triples
to the SPARQL gods.

Let us first recall some basic terminology. A *solution* is defined as a mapping
from variables to RDF terms, for example `{ ?x -> "doof", ?y -> 42 }`. If two
solutions `l` and `r` agree on the variables they have in common, we can
combine them into a new solution `l ∪ r`. For example, if `l = { ?x ->
"doof", ?y -> 42 }` and `r = { ?y -> 42, ?z -> "bloed" }`, we can combine
them into `l ∪ r = { ?x -> "doof", ?y -> 42, ?z -> "bloed" }`. So far, so good.

For `OPTIONAL`, QLever implements the following. The set of solutions of the
left-hand side `L` and the set of solutions of the right-hand side `R` are
computed independently. The resulting set of solutions consists of all pairs `l
∪ r` where `l` is a solution of `L` and `r` is a solution of `R` that agree on
the variables they have in common (in particular, they agree if they have no
variables in common). In addition, all solutions `l` of `L` for which there is
no solution `r` of `R` that agrees with `l` on the variables they have in
common, are also included in the result.

When there are no `FILTER`s on the right-hand side, or the `FILTER`s on the
right-hand side only refer to variables that are also bound on the right-hand
side, or all `FILTER`s that refer to variables that are only bound on the
left-hand side are nested inside other group graph patterns on the right-hand
side, then this is 100% compliant with the standard. Let us hence assume that
there is a `FILTER` on the outermost level of the right-hand side (not nested
inside another group graph pattern) that refers to a variable that is only
bound on the left-hand side.

The SPARQL 1.1 standard dictates that a `FILTER` on the outermost level of the
right-hand side of an `OPTIONAL` is **not** used to filter the group graph
pattern on the right-hand side, but instead that it is used to determine
whether a pair of solutions `l` and `r` agree. For example, consider `l = { ?x
-> "doof", ?y -> 42 }` and `r = { ?y -> 42, ?z -> "bloed" }`, and that the
right-hand side has `FILTER(?x = "doof")` on the outermost level (not nested
inside another group graph pattern). Then, in QLever's implementation, `r`
would not be part of the solution set for `R` because `?x` is not bound in `r`,
and hence the `FILTER` condition produces a so-called type error, which is
treated like `false`. If no other solutions from `R` match with `l`, the result
would then include `l` alone. However, according to the SPARQL 1.1 standard,
`r` is in the solution set of `R` (which is computed without considering the
`FILTER`), and `l` and `r` agree on their common variable (`?y` in this case),
and the `FILTER` condition `?x = "doof"` evaluates to `true` on `l ∪ r`.
Therefore, the result would include `l ∪ r` in this case, and not just `l`.

Fair enough, you might say, expecting that `EXISTS` is defined analogously by
the SPARQL 1.1 standard. That is, for each solution `l` of the left-hand side
`L`, evaluate to `true` if there is a solution `r` of the right-hand side `R`,
for which the `OPTIONAL` above would include `l ∪ r` in the result, and to
`false` otherwise. Alas, that is **not** how `EXISTS` is defined by the SPARQL
1.1 standard, at least not exactly.

According to the standard, `EXISTS` is evaluated using so-called
**substitution** semantics. This means that for every solution `l` on the
left-hand side `L`, `l` is substituted into the right-hand side `R`. Unlike for
`OPTIONAL`, this substitution also applies to group graph patterns that are
nested inside `R`. If the resulting solution set of `R` (after substitution) is
non-empty, then `EXISTS` evaluates to `true`, otherwise to `false`.

When the only `FILTER`s on the right-hand side that use variables from the
left-hand side are on the outermost level of `R`, then this definition of
`EXISTS` agrees with the one you would expect by analogy to `OPTIONAL`. However,
when there are nested group graph patterns on the right-hand side that contain
`FILTER`s that use variables from the left-hand side, the results can differ.
Just consider the example from above, and assume that the `FILTER(?x = "doof")`
is nested inside another group graph pattern on the right-hand side. With
`OPTIONAL`, the result would then no longer include `l ∪ r`, because `r` would
not be part of the solution set of `R` (the `FILTER` would produce a type error
now). However, with `EXISTS`, after substituting `l` into `R`, the `FILTER` would
evaluate to `true`, and hence `r` would be part of the solution set of `R` after
substitution, and hence `EXISTS` would evaluate to `true`.

You may wonder why `EXISTS` is defined via substitution semantics in the SPARQL
1.1 standard, unlike any other construct or function in SPARQL. The reason is
probably that if you want the semantics to be that way, then substitution
semantics is the simplest way to define this. This leaves open the question why
`OPTIONAL` and `EXISTS` should have different semantics in the first place. The
reason is probably that certain queries are easier to express this way.
Whatever it is or was, we don't think that was a good idea because it makes the
standard extremely complicated to understand regarding these specific corner
cases.

All that being said, QLever should of course have an option to be compliant
with the SPARQL 1.1 standard also regarding these subtle corner cases, and we
are working on adding such an option (reluctantly, because we are allergic to
mathematical ugliness).
