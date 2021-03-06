import argparse
import csv
from pathlib import Path
from typing import Iterable
import time

import stanza
from stanza_batch import batch

def file_path(argument_str: str) -> Path:
    '''
    :param argument_str: String from a given argument.
    :returns: Converts argument String to Path type.
    '''
    return Path(argument_str).resolve()

def yield_paragraphs(fp: Path) -> Iterable[str]:
    '''
    Given a file path to a text it will iteratively 
    yield each paragraph within the text until the end of the file.

    A paragraph is defined as continuos block of text. As soon as a blank new 
    line exists a new paragraph is started and the old paragraph is yielded.

    :param fp: File path to a text.
    :returns: Yields paragraphs of text from the file in order from start of 
              file to the end.
    '''
    with fp.open('r', encoding='utf-8-sig') as _file:
        current_paragraph = ''
        for line in _file:
            if line.strip():
                current_paragraph += line
            elif current_paragraph:
                yield current_paragraph
                current_paragraph = ''
        if current_paragraph.strip():
            yield current_paragraph

if __name__ == '__main__':
    program_description = ('Process the text within the given file (1st argument) '
                           'using Stanza English NER model and writes all Entities to'
                           'a given TSV file (2nd argument) with the following structure:'
                           '{paragraph_number}\t{entity text}\t{entity label}'
                           '\t{start character offset}\t{end character offset}')
    parser = argparse.ArgumentParser(description=program_description)
    parser.add_argument('text_file_path', type=file_path, 
                        help='File path to the text to process e.g. Alice in Wonderland.')
    parser.add_argument('output_file_path', type=file_path,
                        help='File path to output the processed data too.')
    parser.add_argument('batch_size', type=int, 
                        help='Number of paragraphs of text for SpaCy to process at a time.')
    parser.add_argument('stanza_model_directory', type=file_path, 
                        help='Directory to store the pre-trained stanza models.')
    args = parser.parse_args()

    text_fp = args.text_file_path
    output_fp = args.output_file_path
    batch_size = args.batch_size
    stanza_model_directory = args.stanza_model_directory
    stanza_model_directory.mkdir(exist_ok=True)

    # Download the relevant stanza model if it has not already been downloaded.
    stanza_processes = 'tokenize,ner'
    stanza.download("en", dir=str(stanza_model_directory), 
                    processors=stanza_processes)
    # load the stanza model
    nlp = stanza.Pipeline(lang='en', processors=stanza_processes, use_gpu=True,
                          tokenize_batch_size=batch_size,
                          ner_batch_size=batch_size,
                          dir=str(stanza_model_directory))
    
    # Load data
    paragraphs_to_process = yield_paragraphs(text_fp)

    # Process data
    paragraph_number = 0
    processing_time: float = 0.0
    with output_fp.open('w+', newline='') as output_file:
        tsv_writer = csv.writer(output_file, delimiter='\t')
        start_time = time.perf_counter()
        for stanza_document in batch(paragraphs_to_process, nlp, batch_size=batch_size):
            for entity in stanza_document.ents:
                tsv_writer.writerow([paragraph_number, entity.text, 
                                     entity.type, 
                                     entity.start_char, 
                                     entity.end_char])
            paragraph_number += 1

        end_time = time.perf_counter()
        processing_time = end_time - start_time