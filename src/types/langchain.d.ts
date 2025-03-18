declare module 'langchain/llms/openai' {
  export class OpenAI {
    constructor(config: { modelName: string; temperature: number });
    call(prompt: string): Promise<string>;
  }
}

declare module 'langchain/document_loaders/fs/pdf' {
  export class PDFLoader {
    constructor(filePath: string);
    load(): Promise<Document[]>;
  }

  interface Document {
    pageContent: string;
    metadata: Record<string, unknown>;
  }
}

declare module 'langchain/text_splitter' {
  export class RecursiveCharacterTextSplitter {
    constructor(config: { chunkSize: number; chunkOverlap: number });
    splitDocuments(documents: Document[]): Promise<Document[]>;
  }

  interface Document {
    pageContent: string;
    metadata: Record<string, unknown>;
  }
}

declare module 'langchain/vectorstores/pinecone' {
  import { OpenAIEmbeddings } from 'langchain/embeddings/openai';
  import { PineconeIndex } from '@pinecone-database/pinecone';
  
  export class PineconeStore {
    static fromDocuments(
      documents: Document[],
      embeddings: OpenAIEmbeddings,
      config: {
        pineconeIndex: PineconeIndex;
        namespace: string;
      }
    ): Promise<PineconeStore>;
  }

  interface Document {
    pageContent: string;
    metadata: Record<string, unknown>;
  }
}

declare module 'langchain/embeddings/openai' {
  export class OpenAIEmbeddings {
    constructor();
  }
} 