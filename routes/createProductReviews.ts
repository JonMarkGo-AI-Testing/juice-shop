/*
 * Copyright (c) 2014-2024 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import { type Request, type Response } from 'express'
import challengeUtils = require('../lib/challengeUtils')
import { reviewsCollection } from '../data/mongodb'

import * as utils from '../lib/utils'
import { challenges } from '../data/datacache'

const security = require('../lib/insecurity')

module.exports = function productReviews () {
  return (req: Request, res: Response) => {
    const user = security.authenticatedUsers.from(req)
    challengeUtils.solveIf(challenges.forgedReviewChallenge, () => { return user && user.data.email !== req.body.author })
    
    // Validate input parameters
    if (typeof req.params.id !== 'string') {
      res.status(400).json({ status: 'error', message: 'Product ID must be a string' })
      return
    }
    
    if (typeof req.body.message !== 'string') {
      res.status(400).json({ status: 'error', message: 'Review message must be a string' })
      return
    }
    
    if (typeof req.body.author !== 'string') {
      res.status(400).json({ status: 'error', message: 'Author must be a string' })
      return
    }
    
    reviewsCollection.insert({
      product: req.params.id,
      message: req.body.message,
      author: req.body.author,
      likesCount: 0,
      likedBy: []
    }).then(() => {
      res.status(201).json({ status: 'success' })
    }, (err: unknown) => {
      res.status(500).json(utils.getErrorMessage(err))
    })
  }
}
