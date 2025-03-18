declare module '@pinecone-database/pinecone' {
  export class PineconeClient {
    constructor();
    init(config: {
      environment: string;
      apiKey: string;
    }): Promise<void>;
    Index(indexName: string): PineconeIndex;
  }

  interface PineconeIndex {
    upsert(params: {
      vectors: Array<{
        id: string;
        values: number[];
        metadata?: Record<string, unknown>;
      }>;
      namespace?: string;
    }): Promise<void>;
    query(params: {
      vector: number[];
      topK: number;
      includeMetadata?: boolean;
      includeValues?: boolean;
      namespace?: string;
    }): Promise<{
      matches: Array<{
        id: string;
        score: number;
        values?: number[];
        metadata?: Record<string, unknown>;
      }>;
    }>;
  }

  export type { PineconeIndex };
} 