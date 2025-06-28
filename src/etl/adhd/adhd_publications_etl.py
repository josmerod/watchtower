import os
import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import pandas as pd
from src.etl.base import BaseETL # BaseETL should handle logger and output_dir
from src.models.adhd import ADHDPublication
# logging is configured by BaseETL, so specific configuration here might not be needed
# import logging

# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

class ADHDPublicationETL(BaseETL):
    def __init__(self, name: str = "adhd_publications", **kwargs):
        super().__init__(name=name, **kwargs)
        # self.base_dir, self.processed_dir, self.json_dir, self.csv_dir are removed
        # os.makedirs for these is also removed, BaseETL handles output_dir

    def extract(self):
        self.logger.info("Starting PubMed data extraction for ADHD publications.")
        search_terms = "ADHD OR \"Attention Deficit Hyperactivity Disorder\""

        esearch_params = {
            "db": "pubmed",
            "term": search_terms,
            "retmax": "10", # Keep small for development
            "usehistory": "y"
        }

        try:
            self.logger.info(f"Searching PubMed with terms: {search_terms}")
            esearch_response = requests.get(ESEARCH_URL, params=esearch_params)
            esearch_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during eSearch request: {e}")
            return []

        try:
            esearch_root = ET.fromstring(esearch_response.content)
        except ET.ParseError as e:
            self.logger.error(f"Error parsing eSearch XML response: {e}")
            return []

        web_env = esearch_root.findtext("WebEnv")
        query_key = esearch_root.findtext("QueryKey")
        pmids = [id_elem.text for id_elem in esearch_root.findall(".//IdList/Id")]

        if not pmids or not web_env or not query_key:
            self.logger.warning("No PMIDs found or WebEnv/QueryKey missing from eSearch response.")
            return []

        self.logger.info(f"Found {len(pmids)} PMIDs. Fetching details...")

        efetch_params = {
            "db": "pubmed",
            "WebEnv": web_env,
            "query_key": query_key,
            "rettype": "abstract",
            "retmode": "xml"
        }

        try:
            efetch_response = requests.get(EFETCH_URL, params=efetch_params)
            efetch_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error during eFetch request: {e}")
            return []

        try:
            efetch_root = ET.fromstring(efetch_response.content)
        except ET.ParseError as e:
            self.logger.error(f"Error parsing eFetch XML response: {e}")
            return []

        articles = []
        for article_elem in efetch_root.findall(".//PubmedArticle"):
            try:
                title = article_elem.findtext(".//ArticleTitle")

                abstract_parts = []
                for abst_text_elem in article_elem.findall(".//Abstract/AbstractText"):
                    if abst_text_elem.text:
                        label = abst_text_elem.get("Label")
                        if label:
                            abstract_parts.append(f"{label}: {abst_text_elem.text}")
                        else:
                            abstract_parts.append(abst_text_elem.text)
                abstract = " ".join(abstract_parts) if abstract_parts else None

                authors = []
                for author_elem in article_elem.findall(".//AuthorList/Author"):
                    last_name = author_elem.findtext("LastName")
                    fore_name = author_elem.findtext("ForeName")
                    collective_name = author_elem.findtext("CollectiveName")
                    if collective_name:
                        authors.append(collective_name)
                    elif last_name and fore_name:
                        authors.append(f"{fore_name} {last_name}")
                    elif last_name:
                         authors.append(last_name)
                    elif fore_name:
                         authors.append(fore_name)


                pub_date_elem = article_elem.find(".//PubDate")
                pub_date = ""
                if pub_date_elem is not None:
                    year = pub_date_elem.findtext("Year")
                    month = pub_date_elem.findtext("Month")
                    day = pub_date_elem.findtext("Day")
                    medline_date = pub_date_elem.findtext("MedlineDate")
                    if year and month and day:
                        pub_date = f"{year}-{month}-{day}"
                    elif year and month:
                        pub_date = f"{year}-{month}"
                    elif year:
                        pub_date = year
                    elif medline_date:
                        pub_date = medline_date

                journal_title = article_elem.findtext(".//Journal/Title")

                doi = None
                for article_id_elem in article_elem.findall(".//PubmedData/ArticleIdList/ArticleId"):
                    if article_id_elem.get("IdType") == "doi":
                        doi = article_id_elem.text
                        break

                pmid_elem = article_elem.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

                articles.append({
                    "title": title,
                    "authors": authors,
                    "publication_date": pub_date,
                    "abstract": abstract,
                    "doi": doi,
                    "url": url,
                    "source": "PubMed",
                    "journal_title": journal_title,
                    "pmid": pmid
                })
            except Exception as e:
                self.logger.error(f"Error parsing article: {e}", exc_info=True)
                # Continue parsing other articles

        self.logger.info(f"Successfully extracted {len(articles)} articles.")
        return articles

    def transform(self, data: list[dict]) -> list[ADHDPublication]:
        self.logger.info(f"Starting transformation for {len(data)} articles.")
        transformed_publications = []
        for paper_data in data:
            try:
                authors_list = paper_data.get("authors", [])
                if not isinstance(authors_list, list) or not all(isinstance(author, str) for author in authors_list):
                    self.logger.warning(f"Authors format incorrect for paper, using default: {paper_data.get('title')}")
                    authors_list = ["Unknown Author"]

                publication_date_str = paper_data.get("publication_date", "")
                if not isinstance(publication_date_str, str):
                    publication_date_str = str(publication_date_str) if publication_date_str is not None else None

                url = paper_data.get("url")
                if not url and paper_data.get('pmid'):
                     url = f"https://pubmed.ncbi.nlm.nih.gov/{paper_data.get('pmid')}/"

                publication = ADHDPublication(
                    title=paper_data.get("title", "No Title Provided"),
                    authors=authors_list,
                    publication_date=publication_date_str,
                    abstract=paper_data.get("abstract"),
                    doi=paper_data.get("doi"),
                    url=url,
                    source="PubMed"
                )
                transformed_publications.append(publication)
            except Exception as e:
                self.logger.error(f"Error transforming article titled '{paper_data.get('title')}': {e}", exc_info=True)

        self.logger.info(f"Successfully transformed {len(transformed_publications)} articles.")
        return transformed_publications

    def load(self, data: list[ADHDPublication]):
        if not data:
            self.logger.warning("No data provided to load method.")
            return

        json_dir = os.path.join(self.output_dir, "json")
        csv_dir = os.path.join(self.output_dir, "csv")
        os.makedirs(json_dir, exist_ok=True)
        os.makedirs(csv_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        papers_dict_list = [paper.model_dump() for paper in data]
        latest_json_file_path = "" # Initialize to prevent reference before assignment in final log
        latest_csv_file_path = ""  # Initialize to prevent reference before assignment in final log

        # JSON Saving
        try:
            json_file_path = os.path.join(json_dir, f"papers_{timestamp}.json")
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(papers_dict_list, f, ensure_ascii=False, indent=4)
            self.logger.info(f"Successfully saved {len(papers_dict_list)} papers to {json_file_path}")

            latest_json_file_path = os.path.join(json_dir, "latest_papers.json")
            with open(latest_json_file_path, 'w', encoding='utf-8') as f:
                json.dump(papers_dict_list, f, ensure_ascii=False, indent=4)
            self.logger.info(f"Successfully updated latest_papers.json at {latest_json_file_path}")
        except IOError as e:
            self.logger.error(f"Error saving JSON file: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during JSON saving: {e}")

        # CSV Saving
        try:
            df = pd.DataFrame(papers_dict_list)
            if 'authors' in df.columns:
                df['authors'] = df['authors'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

            csv_file_path = os.path.join(csv_dir, f"papers_{timestamp}.csv")
            df.to_csv(csv_file_path, index=False, encoding='utf-8')
            self.logger.info(f"Successfully saved {len(df)} papers to {csv_file_path}")

            latest_csv_file_path = os.path.join(csv_dir, "latest_papers.csv")
            df.to_csv(latest_csv_file_path, index=False, encoding='utf-8')
            self.logger.info(f"Successfully updated latest_papers.csv at {latest_csv_file_path}")
        except pd.errors.PandasError as e:
            self.logger.error(f"Pandas DataFrame error during CSV saving: {e}")
        except IOError as e:
            self.logger.error(f"Error saving CSV file: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during CSV saving: {e}")

        if latest_json_file_path and latest_csv_file_path:
            self.logger.info(f"Load process completed for {len(data)} papers. Latest files are at: {latest_json_file_path} and {latest_csv_file_path}")
        else:
            self.logger.warning(f"Load process completed for {len(data)} papers, but one or both latest file paths were not set due to errors.")

    def run(self):
        self.logger.info(f"Starting ETL pipeline: {self.name}")
        try:
            extracted_data = self.extract()
            if not extracted_data:
                self.logger.warning("Extraction yielded no data. Skipping transform and load.")
                return

            transformed_data = self.transform(extracted_data)
            if not transformed_data:
                self.logger.warning("Transformation yielded no data. Skipping load.")
                return

            self.load(transformed_data)
            self.logger.info(f"ETL pipeline: {self.name} completed successfully.")
        except Exception as e:
            self.logger.error(f"Error during ETL pipeline: {self.name}: {e}", exc_info=True)
            # Depending on desired behavior, you might re-raise or handle specific exceptions differently
            # For now, just logging and exiting the run method

if __name__ == "__main__":
    # Example: Initialize with default name and settings
    # This assumes BaseETL and its logger are set up correctly when no args are passed.
    # For production, you might pass specific configurations.
    etl_processor = ADHDPublicationETL()
    etl_processor.run()
