`wait_for_port` is a simple container to do one thing: wait until a specified
container is listening on a port.

If the port is 5432, it also attempts to log in to Postgres with the given
credentials, since Postgres can be listening on port 5432 but still not yet
really ready to serve requests.

## Examples

```bash
docker run --rm --name wfp -v /var/run/docker.sock:/var/run/docker.sock \
    wait_for_port \
    --container somecontainer \
    --port 12345 \
    --timeout 10
```
Run the container and wait for container `somecontainer` to start listening on
port `12345`. Time out after `10` seconds.

```bash
docker run --rm --name wfp -v /var/run/docker.sock:/var/run/docker.sock \
    wait_for_port \
    --container somedbcontainer \
    --port 5432 \
    --timeout 100 \
    --pg_database "$POSTGRES_DB" \
    --pg_user "$POSTGRES_USER" \
    --pg_password "$POSTGRES_PASSWORD"
```
Run the container and wait for container `somedbcontainer` to start listening
on port `5432` and accept the credentials to connect to the database.
Time out after `100` seconds.

## Use-Case

When using [crane](https://www.craneup.tech/) (or docker-compose, or similar),
use a post-start hook to ensure a container is started after the container(s)
it depends on is/are listening for incoming connections.

```yaml
containers:
  slowstartingcontainer:
    build: {...}
    image: company.org/slowstartingcontainer
    run: {...}

  dependentcontainer:
    build: {...}
    image: company.org/dependentcontainer
    run:
      ...
      link:
        - slowstartingcontainer
      ...

hooks:
  slowstartingcontainer:
    post-start: "docker run --rm --name wfp -v /var/run/docker.sock:/var/run/docker.sock wait_for_port:latest --container slowstartingcontainer --port=12345 --timeout=3600"
```
