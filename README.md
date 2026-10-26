# Asset Intelligence

**Open-source multimodal AI for infrastructure asset intelligence.**

> **Status: Work in Progress · Initial Repository Commit**
>
> This repository is at the beginning of development. The project scope, architecture, implementation, and evaluation are evolving. Features described below are planned, not claims of completed functionality.

## Overview

Asset Intelligence is an open-source project exploring how multimodal AI can help turn infrastructure inspection evidence into structured, reviewable asset information.

The intended workflow combines inspection photographs, maintenance notes, and relevant asset context to produce structured observations, identify missing information, and prepare draft maintenance findings for human review.

The goal is to go beyond image captioning by exploring a verifiable, multi-step AI workflow with structured outputs, validation, traceable evidence, and human oversight.

Development will use **Meta AI models** as a core part of the workflow.

## Project Goals

- **Multimodal interpretation:** Explore how AI can connect visual inspection evidence with written maintenance notes.
- **Structured extraction:** Convert relevant observations into consistent, machine-readable data.
- **Evidence traceability:** Keep findings linked to their supporting inputs and distinguish observations from assumptions.
- **Validation and uncertainty:** Check required fields, identify missing context, and flag results that need further review.
- **Human oversight:** Prepare draft findings and maintenance actions for review rather than treating model output as authoritative.
- **Integration:** Explore a clearly separated integration layer for connecting to asset-management systems through authenticated APIs.

## Development Status

This is the first public repository commit. The project is under active development, and the following items represent the intended development direction.

- [ ] Define the initial use case and data schema.
- [ ] Establish the application architecture and API boundaries.
- [ ] Integrate a Meta model for the selected multimodal workflow.
- [ ] Build an initial inspection-evidence processing pipeline.
- [ ] Add structured-output validation and missing-evidence checks.
- [ ] Implement a human-review step.
- [ ] Create synthetic sample data and reproducible tests.
- [ ] Demonstrate the workflow from input evidence to a reviewable result.
- [ ] Evaluate output quality, traceability, and failure cases.
- [ ] Document setup, configuration, and usage as the implementation develops.

The checklist will be updated as work is completed. Planned features should not be interpreted as implemented or production-ready.

## Architecture Direction

The intended workflow is:

1. **Input:** Receive an inspection photograph, maintenance note, or other authorized asset evidence.
2. **Interpretation:** Use a Meta model to analyze the relevant input.
3. **Context:** Associate the evidence with relevant asset information when available and authorized.
4. **Validation:** Check the output against a defined schema and identify missing or uncertain information.
5. **Review:** Present evidence-linked findings and draft actions for human review.
6. **Integration:** Where configured, pass approved data through an authenticated integration boundary.

This workflow is a design direction, not a description of a completed implementation. The specific models, interfaces, and processing steps will be documented as they are built and tested.

## Relationship to Manage Assets

Asset Intelligence is a separate, public-facing development project intended to explore AI capabilities that may integrate with **Manage Assets**, a proprietary asset-management platform.

The separation is deliberate:

- This repository is intended for the open-source AI workflow, integration interfaces, tests, examples, and documentation released here.
- The proprietary Manage Assets application and its private implementation are outside the scope of this repository.
- Any connection to Manage Assets will use an explicitly configured, authenticated API boundary where supported.
- Private source code, credentials, production records, and confidential data must not be committed to this repository.

No access to the proprietary platform is implied by cloning this project. Integration capabilities will be documented once implemented and available for testing.

## Technology

**Planned core dependency:** Meta AI models, accessed through an appropriate supported API or model deployment.

Additional languages, libraries, infrastructure, and model-serving options will be selected and documented as implementation requirements become clear.

This initial README does not imply that any particular model, API, framework, or deployment target has already been integrated.

## Getting Started

The repository is being established. Installation and execution instructions will be added when the initial working implementation and its dependencies are available.

For now, you can:

1. Review the project goals and development checklist.
2. Follow the repository for implementation updates.
3. Open an issue to discuss a specific technical question or proposed improvement.

No working application, API credentials, or production deployment is promised by this initial commit.

## Responsible Use

Infrastructure information can affect operational decisions. Model-generated observations are not verified facts merely because they are presented in structured form.

The project intends to emphasize:

- Human review of generated findings.
- Clear separation between observed evidence and model interpretation.
- Validation of structured outputs.
- Explicit handling of missing information and uncertainty.
- Use of authorized data and appropriately protected credentials.
- Testing and documentation of limitations.

The project is not intended to replace qualified inspections, engineering judgment, safety procedures, or established maintenance protocols.

## Contributing

Early contributions, technical discussion, and focused feedback are welcome as the project takes shape.

Please open an issue before submitting a substantial change so the proposed work can be discussed in the context of the project's scope and architecture.

Contributions must respect the repository's license, data permissions, security requirements, and the separation between this public project and proprietary systems.

By submitting a contribution, you agree that it may be distributed under
the terms of the Apache License, Version 2.0.

## License

This project is licensed under the **Apache License, Version 2.0**.

- Full license text: [`LICENSE`](LICENSE)
- Copyright and attribution: [`NOTICE`](NOTICE)

Copyright 2026 Monica Peters.

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
License for the specific language governing permissions and limitations
under the License.

## Project Information

- **Project:** Asset Intelligence
- **Focus:** Multimodal AI, infrastructure asset intelligence, structured data extraction, and verifiable workflows
- **Development stage:** Initial public commit
- **Primary model ecosystem:** Meta AI

---

*Built as an evolving exploration of practical, evidence-grounded AI for physical infrastructure. Implementation details, evaluation results, and supported integrations will be published as they become available.*