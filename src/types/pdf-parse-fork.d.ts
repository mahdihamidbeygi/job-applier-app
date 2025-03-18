declare module 'pdf-parse-fork' {
  interface PDFInfo {
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
  }

  interface PDFMetadata {
    'dc:creator'?: string;
    'dc:title'?: string;
    'dc:subject'?: string;
    'dc:description'?: string;
    'dc:publisher'?: string;
    'dc:contributor'?: string;
    'dc:date'?: string;
    'dc:type'?: string;
    'dc:format'?: string;
    'dc:identifier'?: string;
    'dc:source'?: string;
    'dc:language'?: string;
    'dc:relation'?: string;
    'dc:coverage'?: string;
    'dc:rights'?: string;
  }

  interface PDFData {
    numpages: number;
    numrender: number;
    info: PDFInfo;
    metadata: PDFMetadata | null;
    text: string;
    version: string;
  }

  interface PDFPageData {
    pageNumber: number;
    text: string;
  }

  function pdfParse(dataBuffer: Buffer, options?: {
    pagerender?: (pageData: PDFPageData) => string;
    max?: number;
    version?: string;
  }): Promise<PDFData>;

  export default pdfParse;
} 