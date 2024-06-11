# asbestos

A mock data system for [Snowflake](https://www.snowflake.com/en/). Test your code using real Snowflake calls just by swapping out the cursor and return whatever data you want, getting away from messy mocks and the occasional odd side effect.

`asbestos` was developed in-house at [SpotOn](https://www.spoton.com/) to solve easy mocking of Snowflake calls across multiple codebases. It fits our use case fully, but if it doesn't implement something you need, we're happy to take pull requests!

!!! info "Why 'Asbestos'?"

    In the classic film _The Wizard of Oz_, the fake snow that they use in the poppy field [is pure asbestos](https://movieweb.com/wizard-of-oz-snow-asbestos/). Thankfully there are much better ways of generating fake snow now that are much less carcinogenic -- most modern fake snow is made from paper byproducts and dyed cellulose fibers!

## Installation

Grab it from PyPI with `pip install asbestos-snow` or `poetry add asbestos-snow`. This is a pure Python package and has no required dependencies of its own. Asbestos takes advantage of modern language features and only supports Python 3.9+.

!!! note

    `asbestos` is not a replacement for [Snowflake's official connector](https://github.com/snowflakedb/snowflake-connector-python). It's intended to run alongside the official connector and let you selectively stub out calls that either aren't finished yet or need to return dummy data for testing purposes.

## Getting started

### [➡️ Setup](setup.md)
### [➡️ Usage](usage.md)
### [➡️ Reference](reference.md)
