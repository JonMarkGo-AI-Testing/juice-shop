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
    // Validate and sanitize inputs
    const sanitizedData = {
      product: String(req.params.id).trim(),
      message: String(req.body.message || '').trim(),
      author: String(req.body.author || '').trim(),
      likesCount: 0,
      likedBy: []
    }

    // Validate required fields
    if (!sanitizedData.product || !sanitizedData.message || !sanitizedData.author) {
      return res.status(400).json({ status: 'error', message: 'Missing required fields' })
    }

    // Use MongoDB's safe query construction
    reviewsCollection.insert(sanitizedData).then(() => {
      res.status(201).json({ status: 'success' })
    }, (err: unknown) => {
      res.status(500).json(utils.getErrorMessage(err))
    })
  }
}
