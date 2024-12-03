import pandas as pd
import json
import os
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import re
import time
from concurrent.futures import ThreadPoolExecutor
import logging
from urllib.parse import urljoin

class MedicalDataCollector:
    def __init__(self, output_dir: str = "medical_data"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Setup logging
        logging.basicConfig(
            filename=os.path.join(output_dir, 'scraping.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Trusted medical websites
        self.medical_sources = {
            'mayoclinic': 'https://www.mayoclinic.org/diseases-conditions',
            'medline': 'https://medlineplus.gov/healthtopics.html',
            'who': 'https://www.who.int/health-topics'
        }
        
        # Headers for web requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def collect_medical_data(self) -> List[Dict]:
        """
        Collect medical data from various sources and format it for training.
        You can implement multiple data collection methods here.
        """
        medical_qa_pairs = []
        
        # Method 1: Load from structured medical datasets
        medical_qa_pairs.extend(self._load_structured_data())
        
        # Method 2: Scrape from medical websites (implement with proper permissions)
        medical_qa_pairs.extend(self._scrape_medical_websites())
        
        # Method 3: Load from local medical text files
        medical_qa_pairs.extend(self._load_local_medical_texts())
        
        return medical_qa_pairs

    def _load_structured_data(self) -> List[Dict]:
        """
        Load data from structured medical datasets
        """
        qa_pairs = []
        
        # Example structure - replace with actual medical dataset
        sample_data = [
            {
                "question": "What are the common symptoms of COVID-19?",
                "context": "COVID-19 symptoms can include fever or chills, cough, shortness of breath, fatigue, muscle aches, headache, loss of taste or smell, sore throat, congestion, nausea, and diarrhea.",
                "answer": "fever or chills, cough, shortness of breath, fatigue, muscle aches, headache, loss of taste or smell, sore throat, congestion, nausea, and diarrhea"
            },
            # Add more structured data here
        ]
        
        qa_pairs.extend(sample_data)
        return qa_pairs

    def _scrape_medical_websites(self) -> List[Dict]:
        """
        Scrape medical data from authorized websites
        """
        qa_pairs = []
        
        try:
            # Scrape Mayo Clinic
            mayo_pairs = self._scrape_mayo_clinic()
            qa_pairs.extend(mayo_pairs)
            logging.info(f"Collected {len(mayo_pairs)} QA pairs from Mayo Clinic")
            
            # Scrape MedlinePlus
            medline_pairs = self._scrape_medline()
            qa_pairs.extend(medline_pairs)
            logging.info(f"Collected {len(medline_pairs)} QA pairs from MedlinePlus")
            
            # Save intermediate results
            self._save_intermediate_results(qa_pairs, 'scraped_data.json')
            
        except Exception as e:
            logging.error(f"Error during web scraping: {str(e)}")
        
        return qa_pairs

    def _scrape_mayo_clinic(self) -> List[Dict]:
        qa_pairs = []
        try:
            response = requests.get(self.medical_sources['mayoclinic'], headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find disease links
            disease_links = soup.find_all('a', href=re.compile(r'/diseases-conditions/.*?/symptoms-causes'))
            
            for link in disease_links[:10]:  # Limit for testing
                disease_url = urljoin(self.medical_sources['mayoclinic'], link['href'])
                time.sleep(1)  # Respect website's rate limiting
                
                try:
                    disease_response = requests.get(disease_url, headers=self.headers)
                    disease_soup = BeautifulSoup(disease_response.text, 'html.parser')
                    
                    # Extract disease information
                    disease_name = disease_soup.find('h1').text.strip()
                    symptoms_section = disease_soup.find('div', {'id': 'symptoms'})
                    causes_section = disease_soup.find('div', {'id': 'causes'})
                    
                    if symptoms_section:
                        qa_pairs.append({
                            "question": f"What are the symptoms of {disease_name}?",
                            "context": symptoms_section.text.strip(),
                            "answer": symptoms_section.text.strip()
                        })
                    
                    if causes_section:
                        qa_pairs.append({
                            "question": f"What causes {disease_name}?",
                            "context": causes_section.text.strip(),
                            "answer": causes_section.text.strip()
                        })
                        
                except Exception as e:
                    logging.error(f"Error scraping disease {disease_url}: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Error scraping Mayo Clinic: {str(e)}")
            
        return qa_pairs

    def _scrape_medline(self) -> List[Dict]:
        qa_pairs = []
        try:
            response = requests.get(self.medical_sources['medline'], headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find health topic links
            topic_links = soup.find_all('a', href=re.compile(r'/health-topics/.*'))
            
            for link in topic_links[:10]:  # Limit for testing
                topic_url = urljoin(self.medical_sources['medline'], link['href'])
                time.sleep(1)  # Respect website's rate limiting
                
                try:
                    topic_response = requests.get(topic_url, headers=self.headers)
                    topic_soup = BeautifulSoup(topic_response.text, 'html.parser')
                    
                    # Extract topic information
                    topic_name = topic_soup.find('h1').text.strip()
                    summary = topic_soup.find('div', {'id': 'topic-summary'})
                    
                    if summary:
                        qa_pairs.append({
                            "question": f"What is {topic_name}?",
                            "context": summary.text.strip(),
                            "answer": summary.text.strip()
                        })
                        
                except Exception as e:
                    logging.error(f"Error scraping topic {topic_url}: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Error scraping MedlinePlus: {str(e)}")
            
        return qa_pairs

    def _load_local_medical_texts(self) -> List[Dict]:
        """
        Load and process local medical text files
        """
        qa_pairs = []
        
        # Load pre-defined medical QA dataset
        medical_qa_data = self._load_medical_qa_dataset()
        qa_pairs.extend(medical_qa_data)
        
        # Process medical text files in the data directory
        text_files_dir = os.path.join(self.output_dir, 'text_files')
        if os.path.exists(text_files_dir):
            for filename in os.listdir(text_files_dir):
                if filename.endswith('.txt'):
                    file_path = os.path.join(text_files_dir, filename)
                    file_qa_pairs = self._process_medical_text_file(file_path)
                    qa_pairs.extend(file_qa_pairs)
        
        return qa_pairs

    def _load_medical_qa_dataset(self) -> List[Dict]:
        """
        Load pre-defined medical QA dataset from JSON file
        """
        qa_pairs = []
        data_file = os.path.join(self.output_dir, 'medical_qa_data.json')
        
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Add greeting interactions
            qa_pairs.extend(data.get('greeting_interactions', []))
            
            # Add medical QA pairs
            qa_pairs.extend(data.get('medical_qa_pairs', []))
            
            # Add appointment interactions
            qa_pairs.extend(data.get('appointment_interactions', []))
            
            # Add emergency responses
            qa_pairs.extend(data.get('emergency_responses', []))
            
            logging.info(f"Loaded {len(qa_pairs)} QA pairs from medical_qa_data.json")
            
        except Exception as e:
            logging.error(f"Error loading medical QA data: {str(e)}")
            # Return empty list if file cannot be loaded
            return []
        
        return qa_pairs

    def _process_medical_text_file(self, file_path: str) -> List[Dict]:
        """
        Process a medical text file and extract QA pairs
        """
        qa_pairs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Split content into sections (this is a simple implementation)
            sections = content.split('\n\n')
            
            for section in sections:
                if len(section.strip()) > 0:
                    # Create a question from the first sentence
                    sentences = section.split('.')
                    if len(sentences) > 1:
                        question = f"What is described in this medical text: {sentences[0].strip()}?"
                        qa_pairs.append({
                            "question": question,
                            "context": section.strip(),
                            "answer": section.strip()
                        })
                        
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")
            
        return qa_pairs

    def _save_intermediate_results(self, data: List[Dict], filename: str):
        """
        Save intermediate results to avoid losing data in case of errors
        """
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def save_to_file(self, data: List[Dict], filename: str = "medical_qa_dataset.json"):
        """
        Save collected data to a file
        """
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    # Initialize collector
    collector = MedicalDataCollector()
    
    # Collect medical data
    medical_qa_pairs = collector.collect_medical_data()
    
    # Save to file
    collector.save_to_file(medical_qa_pairs)
    
    print(f"Collected {len(medical_qa_pairs)} medical Q&A pairs")

if __name__ == "__main__":
    main()
