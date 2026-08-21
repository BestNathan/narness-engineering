// strict-lints.rs — paste into each crate's lib.rs / main.rs (STRICT tier)
//
// The strictest clippy tier (see references/rust-lint.md §5): `forbid` is
// un-overridable downstream; `deny` makes the lint a compile error on every
// build — the L5 control, no script invocation needed. These are the canonical
// "feature bans" that make panicking error paths and unchecked arithmetic
// impossible to slip past a build.

// safety-critical: no unsafe without a project-wide opt-out.
// Remove only if your domain legitimately needs unsafe.
#![forbid(unsafe_code)]

// no panicking error paths in production code
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic)]

// no silent integer overflow / unchecked indexing
#![deny(clippy::arithmetic_side_effects)]
#![deny(clippy::indexing_slicing)]

// every #[allow] must carry a reason, so exceptions stay visible and reviewable
#![deny(clippy::allow_attributes_without_reason)]
