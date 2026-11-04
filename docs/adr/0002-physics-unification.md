# ADR 0002: Connect the physics through shared variables, not a merged model

**Status:** accepted, 2026-11-03.

**Context.** The two domains do not follow the same physics. A wave equation and a diffusion equation differ in form and in the time and length scales they describe. Yet water and waves act on the same material.

**Decision.** Each governing equation stays a separate `PhysicalModel`. Models connect only through shared `StateVariable` and `Compartment` nodes and through `CouplingMechanism` nodes that name a constitutive link, such as Biot poroelasticity or Gassmann fluid substitution. Methods and sensors carry scale ranges, and opportunities require scale overlap.

**Consequences.** Each field keeps its own formulation and terms. Mechanism reviews become concrete: which variable forces which response, through what physics, in which compartment. The cost is the crosswalk between domain terms and shared variables, which needs review by both fields, and scale ranges that each need a cited source.
