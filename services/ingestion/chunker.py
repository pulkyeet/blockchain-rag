import uuid
import tiktoken
from shared.contracts import Chunk

# token aware sliding window chunker using cl100k_base
class TokenChunker:
    def __init__(self, chunk_size: int=512, overlap: int=50):
        self.enc = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        metadata = metadata or {}
        tokens = self.enc.encode(text)
        chunks, start, idx = [],0,0

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunks.append(Chunk(
                id=str(uuid.uuid4()),
                text=self.enc.decode(chunk_tokens),
                metadata={**metadata, "chunk_index": idx, "token_count": len(chunk_tokens)},
            ))

            if end==len(tokens):
                break
            start += self.chunk_size - self.overlap
            idx+=1
        
        return chunks