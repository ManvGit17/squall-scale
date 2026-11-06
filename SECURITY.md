# Security policy

## Supported versions

This project is pre-1.0 and under active development; fixes land on the default branch.

## Reporting a vulnerability

Please report suspected vulnerabilities privately rather than in a public issue:

- Open a [private security advisory](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability)
  on this repository, or
- contact the maintainer (**@ManvGit17**) through GitHub.

Please include steps to reproduce and the impact you observed. You'll get an acknowledgement, and a
fix or mitigation plan once the report is confirmed.

## Scope note

This is a self-hosted demonstration platform. The controller mounts the Docker socket and the load
generator can drive heavy traffic — run it on a machine you control, not exposed to the public
internet, and never point the load generator at hosts you don't own.
