ALTER ROLE rag_readonly WITH LOGIN;

GRANT SELECT ON addresses, contracts, token_transfers TO rag_readonly;

ALTER DEFAULT PRIVILEGES FOR ROLE rag GRANT SELECT ON TABLES TO rag_readonly;