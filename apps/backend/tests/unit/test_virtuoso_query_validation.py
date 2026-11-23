import unittest

from models.virtuoso_model import VirtuosoModel


class TestVirtuosoQueryValidation(unittest.TestCase):
    def test_rejects_update_queries_before_execution(self) -> None:
        model = VirtuosoModel()
        with self.assertRaises(PermissionError):
            model.run_custom_query("INSERT DATA { <https://a> <https://b> <https://c> . }")

    def test_rejects_invalid_syntax_before_execution(self) -> None:
        model = VirtuosoModel()
        with self.assertRaises(ValueError):
            model.run_custom_query("SELECT ?s WHERE { ?s ?p ?o ")

    def test_prepares_update_with_default_graph_when_graph_clause_missing(self) -> None:
        model = VirtuosoModel()
        query = "INSERT DATA { <https://example.org/a> <https://example.org/b> <https://example.org/c> . }"
        prepared = model._prepare_update_query(query)

        self.assertIn("DEFINE input:default-graph-uri <", prepared)
        self.assertIn(query, prepared)

    def test_keeps_update_unchanged_when_graph_clause_present(self) -> None:
        model = VirtuosoModel()
        query = (
            "INSERT DATA { GRAPH <http://segb/events> "
            "{ <https://example.org/a> <https://example.org/b> <https://example.org/c> . } }"
        )
        prepared = model._prepare_update_query(query)

        self.assertEqual(query, prepared)

    def test_validate_query_rejects_unknown_operation_keyword(self) -> None:
        model = VirtuosoModel()
        result = model.validate_query("FOOBAR ?s WHERE { ?s ?p ?o }")

        self.assertFalse(result["valid"])
        self.assertEqual(result["query_kind"], "unknown")

    def test_prologue_and_query_form_may_share_a_line(self) -> None:
        """SPARQL treats whitespace between the prologue and the query form as insignificant (#58)."""
        model = VirtuosoModel()
        cases = {
            "one prefix": "PREFIX schema: <http://schema.org/> SELECT ?t WHERE { ?m schema:text ?t } LIMIT 1",
            "two prefixes": (
                "PREFIX schema: <http://schema.org/> PREFIX prov: <http://www.w3.org/ns/prov#> "
                "SELECT ?t WHERE { ?m schema:text ?t }"
            ),
            "empty prefix": "PREFIX : <http://example.org/> SELECT ?s WHERE { ?s :p ?o }",
            "base and prefix": "BASE <http://example.org/> PREFIX ex: <http://example.org/> SELECT ?s { ?s ex:p ?o }",
            "lowercase keywords": "prefix ex: <http://example.org/> select ?s { ?s ex:p ?o }",
            "comment then one line": "# note\nPREFIX ex: <http://example.org/> SELECT ?s { ?s ex:p ?o }",
            "separate lines (already worked)": "PREFIX ex: <http://example.org/>\nSELECT ?s { ?s ex:p ?o }",
        }
        for name, query in cases.items():
            with self.subTest(name):
                self.assertEqual(model._query_kind(query), "select")
                self.assertTrue(model.validate_query(query)["valid"], model.validate_query(query)["message"])

    def test_an_update_after_a_prologue_on_the_same_line_is_still_refused(self) -> None:
        model = VirtuosoModel()
        query = "PREFIX ex: <http://example.org/> INSERT DATA { ex:a ex:b ex:c . }"

        self.assertEqual(model._query_kind(query), "update")
        with self.assertRaises(PermissionError):
            model.run_custom_query(query)


if __name__ == "__main__":
    unittest.main()
