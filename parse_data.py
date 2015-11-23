#!/usr/bin/python

from collections import defaultdict
import random
import sys

# identifiers for the lines in the file
ASIN = "ASIN:";
SIMILAR = "similar:";


""" 
create the various graphs from the file

users_who_reviewed_product
    key = (int) product node ID
    value = set of (int) user IDs that reviewed the product

products_users_purchased
    key = (int) user node ID
    value = set of (int) product IDs that the user purchased

product_graph
    key = (int) product ID
    value = set of tuples ((int) co-purchased product, (float) edge weight)

"""
def parse_file(filename):
    # the next two maps are temporarily used to store mappings from amazon 
    # string user and product IDs to integers
    amazonid_to_id = dict()
    user_to_id = dict()

    users_who_reviewed_product = defaultdict(set)
    products_users_purchased = defaultdict(set)
    product_graph = defaultdict(set)

    products_processed = 0
    next_user_id = 1
    next_product_id = 1

    # info for the current product in the data file
    current_product_copurchased = list()
    current_product_users_who_reviewed = list()
    current_product_id = None
    current_product_amazon_id = None

    with open(filename, 'r') as data_file:
        for line in data_file:
            line = line.strip(' ').split()
            if not line and current_product_amazon_id:
                # on empty file, store the current product info in the graphs
                products_processed += 1
                if (products_processed % 1000 == 0):
                    print products_processed
                for user in current_product_users_who_reviewed:
                    products_users_purchased[user].add(current_product_id)
                    users_who_reviewed_product[current_product_id].add(user)
                for copurchased in current_product_copurchased:
                    product_graph[copurchased].add((current_product_id, 0))
                    product_graph[current_product_id].add((copurchased, 0))

                # reset the current product information
                current_product_copurchased = list()
                current_product_users_who_reviewed = list()
                current_product_id = None
                current_product_amazon_id = None
                continue

            elif line[0] == ASIN:
                # this identifier means we've started a new product in the file
                current_product_amazon_id = line[1]
                if amazonid_to_id.get(current_product_amazon_id, None):
                    current_product_id = amazonid_to_id[current_product_amazon_id]
                else:
                    amazonid_to_id[current_product_amazon_id] = next_product_id
                    current_product_id = next_product_id
                    next_product_id += 1

            elif line[0] == SIMILAR and line[1] > 0:
                # store copurchased products
                copurchased_products = line[2:]
                for product in copurchased_products:
                    if amazonid_to_id.get(product, None):
                        current_product_copurchased.append(amazonid_to_id[product])
                    else:
                        amazonid_to_id[product] = next_product_id
                        current_product_copurchased.append(next_product_id)
                        next_product_id += 1

            elif line[0].startswith('1') or line[0].startswith('2'):
                # stores reviewed products
                reviewer = line[2]
                if user_to_id.get(reviewer, None):
                    current_product_users_who_reviewed.append(user_to_id[reviewer])
                else:
                    user_to_id[reviewer] = next_user_id
                    current_product_users_who_reviewed.append(next_user_id)
                    next_user_id += 1

    return users_who_reviewed_product, products_users_purchased, product_graph


"""
creates the test set by choosing number_test_purchases to isolate. we store
pairs of userID->productID and remove those pairs from the
users_who_reviewed_product and products_users_purchased graphs
"""
number_test_purchases = 1000
def extract_test_set(user_purchases, product_reviewers):
    test_set = set()
    for i in range(number_test_purchases):
        random_user = random.randint(0, len(user_purchases))
        purchased_products = user_purchases[random_user]
        if len(purchased_products) == 0:
            # if the user didn't purchase anyitems, move to the next one
            i -= 1
            continue
        random_product = random.sample(purchased_products, 1)[0]
        test_set.add((random_user, random_product))
        user_purchases.get(random_user).discard(random_product)
        product_reviewers.get(random_product).discard(random_user)

    return test_set, user_purchases, product_reviewers


# get the score for a product to co-purchased product relationship
def get_score(product, copurchased_product, product_reviewers, user_purchases):
    edge_sum = 0
    for reviewer in product_reviewers[product]:
        if reviewer in product_reviewers[copurchased_product]:
            edge_sum += 1.0 / float(len(user_purchases[reviewer]))

    return edge_sum


# weight the product_graph using the formula from the Zhou paper
def weight_graph(product_graph, user_purchases, product_reviewers):
    for product, edges in product_graph.iteritems():
        new_edges = set()
        for edge in edges:
            copurchased_product = edge[0]
            o_j = len(product_reviewers[copurchased_product])
            if o_j == 0:
                weight = 0
            else:
                score = get_score(product, copurchased_product, product_reviewers, user_purchases)
                weight = float(score) / float(o_j)
            new_edges.add((copurchased_product, weight))
        product_graph[product] = new_edges

    return product_graph


# get recommended products for a particular user
number_predictions = 10
def make_baseline_prediction(user, user_purchases, product_graph):
    candidates = list()
    for product in user_purchases[user]:
        candidates += list(product_graph[product])
    candidates = [pair[0] for pair in sorted(candidates, reverse=True, key=lambda pair: pair[1])]
    
    return candidates[:number_predictions]


# calculate the accuracy of baseline predictions using just the product graph
def baseline_predictions(test_set, user_purchases, product_reviewers, product_graph):
    number_correct = 0
    for test_user, test_product in test_set:
        predictions = make_baseline_prediction(test_user, user_purchases, product_graph)
        if test_product in predictions:
            number_correct += 1

    print "number_correct: ", number_correct
    print "percentage of correct predictions: ", 100.0 * number_correct / float(len(test_set)), "%"


def main():
    argv = sys.argv
    filename = argv[1]
    users_who_reviewed_product, products_users_purchased, product_graph = parse_file(filename)

    test_set, products_users_purchased, users_who_reviewed_product = extract_test_set(products_users_purchased, users_who_reviewed_product)

    product_graph = weight_graph(product_graph, products_users_purchased, users_who_reviewed_product)

    baseline_predictions(test_set, products_users_purchased, users_who_reviewed_product, product_graph)


if __name__ == '__main__':
    main()