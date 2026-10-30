# Technical decisions

| Decision | Reason | Trade-off |
|---|---|---|
| Standard-library Python API instead of requested Express | Python 3 is installed; API stays runnable without network packages. npm offline install failed because registry metadata is missing. | Does not demonstrate Express/Node implementation. |
| Static browser-native HTML/CSS/JS instead of requested Angular | No Angular CLI/compiler or TypeScript compiler is installed; package network is blocked; this laptop has limited RAM. | No Angular component/test/build pipeline. |
| SQLite instead of PostgreSQL | Python `sqlite3` is built in, keeps demo portable and no service running. | Single-node embedded database; PostgreSQL migration is not implemented. |
| Same-origin cookie sessions | Avoids exposing bearer tokens to JavaScript and removes CORS complexity. | HTTPS Secure cookies must be enabled behind an HTTPS reverse proxy. |
| Synthetic `.invalid` contact addresses | Reserved non-deliverable domain reduces accidental disclosure/contact. | Input profile intentionally narrower than a production directory. |
| Naive mean baseline and MAD anomaly score | Small, explainable methods can be reviewed and reproduced. | Not validated forecasting; small sample; no claim of predictive accuracy. |
| Loopback by default; remote bind requires read-only mode | Prevents accidental exposure of a mutable local demo. | Public deployment needs HTTPS proxy and environment configuration. |

No paid services, container platform, AI model, or external runtime dependency is required by the local version.
