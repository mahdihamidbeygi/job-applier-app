declare module 'pdf.js-extract' {
  export interface PDFExtractText {
    str: string;
    x: number;
    y: number;
    dir: string;
    fontName: string;
  }

  export interface PDFExtractPage {
    content: PDFExtractText[];
  }

  export interface PDFExtractResult {
    pages: PDFExtractPage[];
    meta: {
      info: {
        PDFFormatVersion: string;
        IsAcroFormPresent: boolean;
        IsXFAPresent: boolean;
        Creator?: string;
        Producer?: string;
        Title?: string;
        Author?: string;
        Subject?: string;
        Keywords?: string;
        CreationDate?: string;
        ModDate?: string;
      };
    };
  }

  export interface PDFExtractOptions {
    max?: number;
    version?: string;
    pagerender?: (pageData: PDFExtractPage) => string;
  }

  export class PDFExtract {
    extractBuffer(buffer: Buffer, options?: PDFExtractOptions): Promise<PDFExtractResult>;
  }
} 