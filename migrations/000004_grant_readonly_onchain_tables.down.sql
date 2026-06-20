ALTER DEFAULT PRIVILEGES FOR ROLE rag REVOKE SELECT ON TABLES FROM rag_readonly;

REVOKE SELECT ON addresses, contracts, token_transfers FROM rag_readonly;

ALTER ROLE rag_readonly WITH NOLOGIN;