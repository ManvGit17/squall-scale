# Build the backend, run its unit tests, and ship a lean runtime image.
#
#   docker build backend                 -> runtime image (default)
#   docker build --target test backend   -> compiles and runs the unit tests

FROM ubuntu:22.04 AS build
RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ make \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN make app

# Test stage: fails the build if any unit test fails.
FROM build AS test
RUN make test

# Runtime stage: just the binary on a clean base.
FROM ubuntu:22.04 AS runtime
WORKDIR /app
COPY --from=build /app/app /app/app
EXPOSE 8080
HEALTHCHECK --interval=5s --timeout=3s --start-period=2s --retries=3 \
    CMD ["/app/app", "healthcheck"]
CMD ["/app/app"]
