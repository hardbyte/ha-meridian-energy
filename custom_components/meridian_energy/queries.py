"""GraphQL query documents for the Meridian Energy Kraken API.

Extracted from Meridian's own web app bundle (app.meridianenergy.nz), which
embeds these as literal `gql` tagged template strings. Kept verbatim so the
server-side field selection stays in sync with what Meridian's own client
requests.
"""

ACCOUNTS_LIST_QUERY = """
query accountsList($activeFrom: DateTime, $allowedBrandCodes: [BrandChoices]) {
  viewer {
    accounts(allowedBrandCodes: $allowedBrandCodes) {
      number
      status
      billingName
      ledgers {
        number
        ledgerType
      }
      ... on AccountType {
        id
        properties(activeFrom: $activeFrom) {
          id
          address
          meterPoints {
            id
            marketIdentifier
          }
        }
      }
    }
  }
}
"""

MEASUREMENTS_ALL_PROPERTIES_QUERY = """
query measurementsAllProperties(
  $accountNumber: String!
  $first: Int!
  $utilityFilters: [UtilityFiltersInput!]
  $startOn: Date
  $endOn: Date
  $startAt: DateTime
  $endAt: DateTime
  $timezone: String
) {
  account(accountNumber: $accountNumber) {
    id
    properties {
      id
      measurements(
        first: $first
        utilityFilters: $utilityFilters
        startOn: $startOn
        endOn: $endOn
        startAt: $startAt
        endAt: $endAt
        timezone: $timezone
      ) {
        edges {
          node {
            source
            value
            unit
            readAt
            ... on IntervalMeasurementType {
              startAt
              endAt
            }
            metaData {
              utilityFilters {
                ... on ElectricityFiltersOutput {
                  readingDirection
                  readingQuality
                  readingFrequencyType
                }
              }
              statistics {
                type
                value
                costInclTax {
                  estimatedAmount
                  costCurrency
                  pricePerUnit {
                    amount
                    unit
                  }
                }
                description
                costExclTax {
                  costCurrency
                  estimatedAmount
                  pricePerUnit {
                    amount
                    unit
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
