import unittest

import server


class LegalDocumentsTest(unittest.TestCase):
    def test_documents_are_full_and_current(self) -> None:
        documents = server.document_seed_data()

        server.validate_document_seed_data(documents)
        self.assertEqual(
            {document["version"] for document in documents},
            {server.LEGAL_DOCUMENT_RELEASE},
        )
        self.assertEqual(
            {document["document_type"] for document in documents},
            {"privacy_policy", "personal_data_consent", "terms"},
        )


if __name__ == "__main__":
    unittest.main()
