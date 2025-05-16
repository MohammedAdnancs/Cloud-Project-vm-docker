#!/usr/bin/env python3

try:
    import HtmlTestRunner
    print("Import successful as: HtmlTestRunner")
except ImportError:
    print("Failed to import as: HtmlTestRunner")

try: 
    import html_testRunner
    print("Import successful as: html_testRunner")
except ImportError:
    print("Failed to import as: html_testRunner")

try:
    from html_testRunner import HTMLTestRunner
    print("Import successful as: from html_testRunner import HTMLTestRunner")
except ImportError:
    print("Failed to import as: from html_testRunner import HTMLTestRunner")

try:
    from HtmlTestRunner import HTMLTestRunner
    print("Import successful as: from HtmlTestRunner import HTMLTestRunner")
except ImportError:
    print("Failed to import as: from HtmlTestRunner import HTMLTestRunner")

try:
    import html.testRunner
    print("Import successful as: html.testRunner")
except ImportError:
    print("Failed to import as: html.testRunner")

print("Done testing imports") 